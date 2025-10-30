#!/usr/bin/env python3
"""
Main entry point for the PDF to LaTeX conversion pipeline
Uses dependency injection and factory pattern for loose coupling
Now with workspace management support
"""
import os
import sys
import argparse
from dotenv import load_dotenv

from src.config_loader import ConfigLoader
from src.factory import ConverterFactory
from src.pipeline import PDFToLatexPipeline
from src.utils import CheckpointManager, LatexIntegrator
from src.workspace_manager import WorkspaceManager


def cmd_workspace_list(workspace_mgr: WorkspaceManager, args):
    """List all workspaces"""
    workspaces = workspace_mgr.list_workspaces()
    
    if not workspaces:
        print("No workspaces found. Create one with: python main.py workspace create")
        return
    
    print(f"\n{'='*80}")
    print(f"{'Workspace':<20} {'Status':<12} {'Last Accessed':<25} {'Current':<8}")
    print(f"{'='*80}")
    
    for ws in workspaces:
        current_marker = "✓" if ws['is_current'] else ""
        print(f"{ws['name']:<20} {ws['status']:<12} {ws['last_accessed'][:19]:<25} {current_marker:<8}")
    
    print(f"{'='*80}\n")


def cmd_workspace_create(workspace_mgr: WorkspaceManager, args):
    """Create a new workspace"""
    try:
        workspace_mgr.create_workspace(
            name=args.name,
            pdf_path=args.pdf_path,
            description=args.description or "",
            set_as_current=not args.no_set_current
        )
    except Exception as e:
        print(f"❌ Error creating workspace: {e}")
        return 1
    return 0


def cmd_workspace_switch(workspace_mgr: WorkspaceManager, args):
    """Switch to a different workspace"""
    try:
        workspace_mgr.set_current_workspace(args.name)
    except Exception as e:
        print(f"❌ Error switching workspace: {e}")
        return 1
    return 0


def cmd_workspace_info(workspace_mgr: WorkspaceManager, args):
    """Show workspace information"""
    workspace_mgr.print_workspace_info(args.name)
    return 0


def cmd_workspace_delete(workspace_mgr: WorkspaceManager, args):
    """Delete a workspace"""
    try:
        # Confirm deletion
        if not args.force:
            response = input(f"Delete workspace '{args.name}'? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return 0
        
        workspace_mgr.delete_workspace(args.name, delete_files=args.delete_files)
    except Exception as e:
        print(f"❌ Error deleting workspace: {e}")
        return 1
    return 0


def cmd_convert(workspace_mgr: WorkspaceManager, args):
    """Run conversion on current workspace or specified PDF"""
    # Load environment variables
    load_dotenv()
    
    # Load configuration
    config = ConfigLoader(args.config)
    
    # Determine PDF path and output directory
    if args.workspace:
        # Use specified workspace
        try:
            workspace_mgr.set_current_workspace(args.workspace)
        except Exception as e:
            print(f"❌ Error: {e}")
            return 1
    
    if args.pdf_path:
        # Direct PDF mode (no workspace)
        pdf_path = args.pdf_path
        output_dir = args.output_dir or config.get_pipeline_config().get('output_dir', 'output')
        print("📄 Running in direct mode (no workspace)")
    else:
        # Workspace mode
        current_ws = workspace_mgr.get_current_workspace()
        if not current_ws:
            print("❌ No workspace specified and no current workspace set.")
            print("   Use: python main.py workspace create <name> <pdf_path>")
            print("   Or: python main.py convert <pdf_path> --output-dir <dir>")
            return 1
        
        paths = workspace_mgr.get_workspace_paths()
        pdf_path = paths['pdf_path']
        output_dir = paths['workspace_dir']
        
        print(f"📂 Using workspace: {current_ws['name']}")
        print(f"📄 PDF: {pdf_path}")
        
        # Update workspace status
        workspace_mgr.update_workspace_status(current_ws['name'], 'processing')
    
    # Get converter configurations
    pdf_config = config.get_converter_config('pdf')
    latex_config = config.get_converter_config('image_to_latex')
    pipeline_config = config.get_pipeline_config()
    
    # Override converter type if specified
    converter_type = args.converter or latex_config.get('type', 'dummy')
    
    # Get API key from environment
    api_key_env = latex_config.get('api_key_env', 'GEMINI_API_KEY')
    api_key = os.getenv(api_key_env)
    
    if converter_type == 'gemini' and not api_key:
        print(f"⚠️ Warning: {api_key_env} not set in environment")
        print(f"   Falling back to dummy converter for testing")
        converter_type = 'dummy'
    
    # Create rate limiter
    rate_limit_config = latex_config.get('rate_limit', {})
    rate_limiter = ConverterFactory.create_rate_limiter(
        max_requests=rate_limit_config.get('max_requests', 2),
        time_window=rate_limit_config.get('time_window', 60)
    )
    
    # Create converters using factory pattern
    pdf_converter = ConverterFactory.create_pdf_converter(
        dpi=pdf_config.get('dpi', 300),
        enable_diff_check=pdf_config.get('enable_diff_check', True)
    )
    
    image_converter = ConverterFactory.create_image_to_latex_converter(
        converter_type=converter_type,
        api_key=api_key,
        model=latex_config.get('model', 'gemini-2.0-flash-exp'),
        max_retries=latex_config.get('max_retries', 3),
        timeout=latex_config.get('timeout', 120),
        retry_delay=latex_config.get('retry_delay', 5),
        rate_limiter=rate_limiter
    )
    
    # Create checkpoint manager and integrator
    checkpoint_file = os.path.join(output_dir, 'checkpoint.json')
    checkpoint_manager = CheckpointManager(checkpoint_file=checkpoint_file)
    
    latex_dir = os.path.join(output_dir, 'latex')
    latex_integrator = LatexIntegrator(output_dir=latex_dir)
    
    # Create pipeline with dependency injection
    pipeline = PDFToLatexPipeline(
        pdf_converter=pdf_converter,
        image_converter=image_converter,
        checkpoint_manager=checkpoint_manager,
        latex_integrator=latex_integrator
    )
    
    # Run pipeline
    result = pipeline.run(
        pdf_path=pdf_path,
        output_dir=output_dir,
        section_prefix=pipeline_config.get('section_prefix', 'notes'),
        create_main_doc=True,
        doc_title=pipeline_config.get('doc_title', 'Converted Notes'),
        resume=not args.no_resume
    )
    
    # Update workspace status if in workspace mode
    if not args.pdf_path:
        current_ws = workspace_mgr.get_current_workspace()
        if current_ws:
            status = 'complete' if result['status'] == 'complete' else 'partial'
            workspace_mgr.update_workspace_status(current_ws['name'], status)
    
    # Print summary
    if result['status'] == 'complete':
        print("\n✅ Conversion completed successfully!")
    else:
        print("\n⚠️ Conversion partially completed (can be resumed)")
    
    return 0


def main():
    """Main entry point with workspace management"""
    
    # Initialize workspace manager
    workspace_mgr = WorkspaceManager()
    
    # Create main parser
    parser = argparse.ArgumentParser(
        description='Convert PDF handwritten notes to LaTeX with workspace management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a workspace
  python main.py workspace create my-notes /path/to/notes.pdf
  
  # Convert current workspace
  python main.py convert
  
  # Convert specific workspace
  python main.py convert --workspace my-notes
  
  # Convert PDF directly (no workspace)
  python main.py convert /path/to/notes.pdf --output-dir output
  
  # List workspaces
  python main.py workspace list
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Workspace subcommands
    workspace_parser = subparsers.add_parser('workspace', help='Manage workspaces')
    workspace_subparsers = workspace_parser.add_subparsers(dest='workspace_command')
    
    # workspace list
    workspace_list = workspace_subparsers.add_parser('list', help='List all workspaces')
    
    # workspace create
    workspace_create = workspace_subparsers.add_parser('create', help='Create a new workspace')
    workspace_create.add_argument('name', help='Workspace name')
    workspace_create.add_argument('pdf_path', help='Path to PDF file')
    workspace_create.add_argument('--description', help='Workspace description')
    workspace_create.add_argument('--no-set-current', action='store_true', 
                                 help='Do not set as current workspace')
    
    # workspace switch
    workspace_switch = workspace_subparsers.add_parser('switch', help='Switch to a workspace')
    workspace_switch.add_argument('name', help='Workspace name')
    
    # workspace info
    workspace_info = workspace_subparsers.add_parser('info', help='Show workspace information')
    workspace_info.add_argument('name', nargs='?', help='Workspace name (current if not specified)')
    
    # workspace delete
    workspace_delete = workspace_subparsers.add_parser('delete', help='Delete a workspace')
    workspace_delete.add_argument('name', help='Workspace name')
    workspace_delete.add_argument('--delete-files', action='store_true',
                                 help='Also delete workspace files')
    workspace_delete.add_argument('--force', action='store_true',
                                 help='Skip confirmation prompt')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert PDF to LaTeX')
    convert_parser.add_argument(
        'pdf_path',
        nargs='?',
        help='Path to PDF file (uses current workspace if not specified)'
    )
    convert_parser.add_argument(
        '--workspace',
        help='Use specific workspace (overrides current)'
    )
    convert_parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    convert_parser.add_argument(
        '--output-dir',
        help='Output directory (only for direct PDF mode)'
    )
    convert_parser.add_argument(
        '--converter',
        choices=['gemini', 'dummy'],
        help='Converter type to use'
    )
    convert_parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh instead of resuming from checkpoint'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'workspace':
        if args.workspace_command == 'list':
            return cmd_workspace_list(workspace_mgr, args)
        elif args.workspace_command == 'create':
            return cmd_workspace_create(workspace_mgr, args)
        elif args.workspace_command == 'switch':
            return cmd_workspace_switch(workspace_mgr, args)
        elif args.workspace_command == 'info':
            return cmd_workspace_info(workspace_mgr, args)
        elif args.workspace_command == 'delete':
            return cmd_workspace_delete(workspace_mgr, args)
        else:
            workspace_parser.print_help()
            return 1
    
    elif args.command == 'convert':
        return cmd_convert(workspace_mgr, args)
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())