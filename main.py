#!/usr/bin/env python3
"""
Main entry point for the PDF to LaTeX conversion pipeline
Uses dependency injection and factory pattern for loose coupling
"""
import os
import argparse
from dotenv import load_dotenv

from src.config_loader import ConfigLoader
from src.factory import ConverterFactory
from src.pipeline import PDFToLatexPipeline
from src.utils import CheckpointManager, LatexIntegrator


def main():
    """Main entry point with configuration-based setup"""
    
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Convert PDF handwritten notes to LaTeX with modular architecture'
    )
    parser.add_argument(
        'pdf_path',
        type=str,
        help='Path to the PDF file to convert'
    )
    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help='Path to configuration file (YAML or JSON). Auto-detects if not specified.'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (overrides config)'
    )
    parser.add_argument(
        '--converter',
        type=str,
        choices=['gemini', 'dummy'],
        default=None,
        help='Converter type to use (overrides config)'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh instead of resuming from checkpoint'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = ConfigLoader(args.config)
    
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
    
    # Get output directory
    output_dir = args.output_dir or pipeline_config.get('output_dir', 'output')
    
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
        pdf_path=args.pdf_path,
        output_dir=output_dir,
        section_prefix=pipeline_config.get('section_prefix', 'notes'),
        create_main_doc=True,
        doc_title=pipeline_config.get('doc_title', 'Converted Notes'),
        resume=not args.no_resume
    )
    
    # Print summary
    if result['status'] == 'complete':
        print("\n✅ Conversion completed successfully!")
    else:
        print("\n⚠️ Conversion partially completed (can be resumed)")
    
    return 0


if __name__ == "__main__":
    exit(main())
