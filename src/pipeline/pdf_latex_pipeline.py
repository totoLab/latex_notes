"""
Complete PDF to LaTeX conversion pipeline with dependency injection
"""
import os
import time
import traceback
from typing import Optional, Dict

from ..converters.base import PDFToImageConverterBase, ImageToLatexConverterBase
from ..converters.latex_error_fixer import LatexErrorFixer
from ..utils import CheckpointManager, LatexIntegrator, LatexCompiler


class PDFToLatexPipeline:
    """
    Complete pipeline orchestrator with retry, resume capability, and dependency injection
    
    This class uses dependency injection to be loosely coupled from specific converter implementations
    """
    
    def __init__(
        self,
        pdf_converter: PDFToImageConverterBase,
        image_converter: ImageToLatexConverterBase,
        checkpoint_manager: Optional[CheckpointManager] = None,
        latex_integrator: Optional[LatexIntegrator] = None,
        latex_compiler: Optional[LatexCompiler] = None,
        latex_error_fixer: Optional[LatexErrorFixer] = None,
        compile_and_fix: bool = False,
        max_fix_attempts: int = 2
    ):
        """
        Initialize pipeline with injected dependencies
        
        Args:
            pdf_converter: PDF to image converter instance
            image_converter: Image to LaTeX converter instance
            checkpoint_manager: Optional checkpoint manager (creates default if None)
            latex_integrator: Optional LaTeX integrator (creates default if None)
            latex_compiler: Optional LaTeX compiler (creates default if None)
            latex_error_fixer: Optional LaTeX error fixer (creates default if None)
            compile_and_fix: Whether to compile and fix errors after each page
            max_fix_attempts: Maximum attempts to fix compilation errors per page
        """
        self.pdf_converter = pdf_converter
        self.image_converter = image_converter
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.latex_integrator = latex_integrator or LatexIntegrator()
        self.latex_compiler = latex_compiler
        self.latex_error_fixer = latex_error_fixer
        self.compile_and_fix = compile_and_fix
        self.max_fix_attempts = max_fix_attempts
    
    def run(
        self,
        pdf_path: str,
        output_dir: str = "output",
        section_prefix: str = "notes",
        create_main_doc: bool = True,
        doc_title: str = "Converted Notes",
        resume: bool = True
    ) -> dict:
        """
        Run complete conversion pipeline with version-aware checkpoint system
        
        Args:
            pdf_path: Path to input PDF
            output_dir: Base output directory
            section_prefix: Prefix for section filenames
            create_main_doc: Whether to create a main document
            doc_title: Title for main document
            resume: Whether to resume from checkpoint if available
            
        Returns:
            Dictionary with paths to generated files
        """
        print(f"\n{'='*60}")
        print(f"PDF to LaTeX Conversion Pipeline")
        print(f"(Modular Architecture with Dependency Injection)")
        print(f"{'='*60}\n")
        
        # Show which converters are being used
        print(f"📦 PDF Converter: {self.pdf_converter.__class__.__name__}")
        print(f"📦 Image Converter: {self.image_converter.__class__.__name__}\n")
        
        # Load checkpoint
        checkpoint = None
        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            if checkpoint and checkpoint.get('pdf') != pdf_path:
                print(f"⚠️ Checkpoint exists but for different PDF. Starting fresh.")
                checkpoint = None
        
        # Initialize checkpoint structure if needed
        if checkpoint is None:
            checkpoint = {
                'pdf': pdf_path,
                'pages': [],
                'main_document_updated': False,
                'main_document_path': None
            }
        
        # Stage 1: Check and update all images
        print("Stage 1: Checking images...")
        image_dir = os.path.join(output_dir, "images")
        images, image_versions = self.pdf_converter.convert(pdf_path, image_dir, checkpoint)
        
        # Update checkpoint with image versions
        for page_num, img_version in image_versions.items():
            page_entry = self.checkpoint_manager.get_page_entry(checkpoint, page_num)
            old_version = page_entry['image_version'] if page_entry else 0
            
            # Update image version and mark if image was updated
            self.checkpoint_manager.update_page_entry(
                checkpoint, 
                page_num,
                image_version=img_version,
                image_updated=(img_version > old_version)
            )
        
        print(f"✓ Checked {len(images)} images\n")
        
        # Stage 2: Process LaTeX for pages where image was updated or latex not done
        print("Stage 2: Processing LaTeX conversions...")
        latex_dir = os.path.join(output_dir, "latex")
        self.latex_integrator.output_dir = latex_dir
        
        # Determine which pages need LaTeX processing
        pages_to_process = []
        pages_updated_images = []
        pages_new = []
        
        for page_num in range(1, len(images) + 1):
            page_entry = self.checkpoint_manager.get_page_entry(checkpoint, page_num)
            
            if page_entry is None:
                # New page
                pages_new.append(page_num)
                pages_to_process.append(page_num)
            elif page_entry['image_version'] > page_entry.get('latex_version', 0):
                # Image is newer than LaTeX
                pages_updated_images.append(page_num)
                pages_to_process.append(page_num)
            elif not page_entry.get('latex_updated', False):
                # LaTeX was never completed
                pages_to_process.append(page_num)
        
        if pages_to_process:
            print(f"📝 Need to process {len(pages_to_process)} page(s):")
            if pages_new:
                print(f"   • {len(pages_new)} new page(s)")
            if pages_updated_images:
                print(f"   • {len(pages_updated_images)} updated image(s)")
            print()
        else:
            print(f"✓ All pages are up to date!\n")
        
        # Save checkpoint after image check
        self.checkpoint_manager.save_checkpoint(checkpoint)
        
        latex_sections = []
        start_time = time.time()
        
        for i, image_path in enumerate(images, start=1):
            # Skip pages that don't need processing
            if i not in pages_to_process:
                # Get existing section file
                section_file = os.path.join(latex_dir, f"{section_prefix}_page{i}.tex")
                if os.path.exists(section_file):
                    latex_sections.append(section_file)
                    
                    # Ensure it's in main document even if skipped
                    if create_main_doc:
                        main_doc_path = os.path.join(output_dir, "main.tex")
                        self.latex_integrator.append_section_to_main(
                            section_file=section_file,
                            main_doc_path=main_doc_path,
                            title=doc_title
                        )
                
                print(f"⏭️ Skipping page {i}/{len(images)} (up to date)")
                continue
            
            try:
                page_entry = self.checkpoint_manager.get_page_entry(checkpoint, i)
                current_img_version = page_entry['image_version'] if page_entry else 1
                
                print(f"\n📄 Processing page {i}/{len(images)} (image v{current_img_version})...")
                
                # Convert image to LaTeX using injected converter
                latex_code = self.image_converter.convert(image_path)
                
                # Compile and fix errors if enabled
                if self.compile_and_fix and self.latex_compiler and self.latex_error_fixer:
                    latex_code = self._compile_and_fix_latex(
                        latex_code,
                        page_num=i,
                        section_title=f"Page {i}",
                        output_dir=latex_dir,
                        max_fix_attempts=self.max_fix_attempts
                    )
                
                # Save as section
                section_file = self.latex_integrator.save_section(
                    latex_code,
                    filename=f"{section_prefix}_page{i}",
                    section_title=f"Page {i}",
                    wrap_in_section=True
                )
                
                latex_sections.append(section_file)
                
                # Append to main document immediately if create_main_doc is enabled
                if create_main_doc:
                    main_doc_path = os.path.join(output_dir, "main.tex")
                    self.latex_integrator.append_section_to_main(
                        section_file=section_file,
                        main_doc_path=main_doc_path,
                        title=doc_title
                    )
                    print(f"✓ Added page {i} to main.tex")
                
                # Update checkpoint - LaTeX is now same version as image
                self.checkpoint_manager.update_page_entry(
                    checkpoint,
                    i,
                    latex_version=current_img_version,
                    latex_updated=True
                )
                
                # Save checkpoint after each successful page
                self.checkpoint_manager.save_checkpoint(checkpoint)
                
                # Calculate estimated time remaining
                elapsed = time.time() - start_time
                processed_count = len([p for p in pages_to_process if p <= i])
                remaining_pages = len(pages_to_process) - processed_count
                
                if processed_count > 0:
                    avg_time_per_page = elapsed / processed_count
                    estimated_remaining = avg_time_per_page * remaining_pages
                    print(f"✓ Page {i}/{len(images)} complete ({processed_count}/{len(pages_to_process)} processed)")
                    if remaining_pages > 0:
                        print(f"   Est. time remaining: {estimated_remaining/60:.1f} minutes")
                
            except Exception as e:
                print(f"\n❌ Failed to process page {i}: {str(e)}")
                print(f"📋 Progress saved. You can resume by running the script again.")
                traceback.print_exc()
                
                # Return partial results
                return {
                    'pdf': pdf_path,
                    'images': images,
                    'latex_sections': latex_sections,
                    'main_document': checkpoint.get('main_document_path'),
                    'checkpoint': checkpoint,
                    'status': 'partial'
                }
        
        print(f"\n✓ All {len(latex_sections)} LaTeX sections ready\n")
        
        # Stage 3: Finalize main document
        main_doc_path = None
        if create_main_doc:
            print("Stage 3: Finalizing main document...")
            main_doc_path = os.path.join(output_dir, "main.tex")
            
            # Main document should already exist from incremental updates
            # But ensure all sections are present (in case of resume)
            if not os.path.exists(main_doc_path):
                # Create it fresh if it doesn't exist
                self.latex_integrator.create_main_document(
                    latex_sections,
                    output_path=main_doc_path,
                    title=doc_title
                )
            else:
                # Verify all sections are included
                for section_file in latex_sections:
                    self.latex_integrator.append_section_to_main(
                        section_file=section_file,
                        main_doc_path=main_doc_path,
                        title=doc_title
                    )
            
            print(f"✓ Main document ready at {main_doc_path}")
            checkpoint['main_document_updated'] = True
            checkpoint['main_document_path'] = main_doc_path
            self.checkpoint_manager.save_checkpoint(checkpoint)
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"Pipeline Complete! 🎉")
        print(f"{'='*60}")
        print(f"\nOutput files:")
        print(f"  Images: {len(images)} files")
        print(f"  LaTeX sections: {len(latex_sections)} files")
        if main_doc_path:
            print(f"  Main document: {main_doc_path}")
        print(f"\nTotal time: {total_time/60:.1f} minutes")
        if len(pages_to_process) > 0:
            print(f"Average time per page: {total_time/len(pages_to_process):.1f} seconds")
        print(f"\nTo compile: cd {output_dir} && xelatex main.tex")
        
        return {
            'pdf': pdf_path,
            'images': images,
            'latex_sections': latex_sections,
            'main_document': main_doc_path,
            'checkpoint': checkpoint,
            'status': 'complete'
        }
    
    def _compile_and_fix_latex(
        self,
        latex_code: str,
        page_num: int,
        section_title: str,
        output_dir: str,
        max_fix_attempts: int = 2
    ) -> str:
        """
        Compile LaTeX code and fix errors if any
        
        Args:
            latex_code: The LaTeX code to compile
            page_num: Page number being processed
            section_title: Title for the section
            output_dir: Directory for temporary files
            max_fix_attempts: Maximum attempts to fix compilation errors
            
        Returns:
            Fixed LaTeX code (or original if no errors or fixing fails)
        """
        import tempfile
        
        print(f"   🔨 Testing compilation for page {page_num}...")
        
        # Create a temporary complete LaTeX document for testing
        temp_latex = self._create_test_document(latex_code, section_title)
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.tex',
            dir=output_dir,
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(temp_latex)
            temp_path = temp_file.name
        
        try:
            # Try to compile
            success, output, errors = self.latex_compiler.compile(temp_path, clean_aux=True)
            
            if success:
                print(f"   ✅ Page {page_num} compiles successfully!")
                return latex_code
            
            # Compilation failed, try to fix
            print(f"   ❌ Page {page_num} has {len(errors)} compilation error(s)")
            
            fixed_code = latex_code
            for attempt in range(1, max_fix_attempts + 1):
                print(f"   🔧 Fix attempt {attempt}/{max_fix_attempts}...")
                
                try:
                    # Use error fixer to fix the code
                    fixed_code = self.latex_error_fixer.fix_errors(
                        latex_code=fixed_code,
                        errors=errors
                    )
                    
                    # Test the fixed code
                    temp_latex_fixed = self._create_test_document(fixed_code, section_title)
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.write(temp_latex_fixed)
                    
                    success, output, errors = self.latex_compiler.compile(temp_path, clean_aux=True)
                    
                    if success:
                        print(f"   ✅ Successfully fixed errors for page {page_num}!")
                        return fixed_code
                    else:
                        print(f"   ⚠️ Still has {len(errors)} error(s) after fix attempt {attempt}")
                        
                except Exception as e:
                    print(f"   ⚠️ Error during fix attempt {attempt}: {str(e)}")
                    
            # All fix attempts failed
            print(f"   ❌ Could not fix all errors after {max_fix_attempts} attempts")
            print(f"   ⚠️ Using original code (may have compilation errors)")
            return latex_code
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
                # Also clean any auxiliary files
                base_path = os.path.splitext(temp_path)[0]
                for ext in ['.aux', '.log', '.out', '.xdv', '.pdf']:
                    aux_file = base_path + ext
                    if os.path.exists(aux_file):
                        os.unlink(aux_file)
            except Exception as e:
                print(f"   ⚠️ Could not clean temporary files: {str(e)}")
    
    def _create_test_document(self, latex_content: str, title: str = "Test") -> str:
        """
        Create a complete LaTeX document for testing compilation
        
        Args:
            latex_content: The LaTeX content to test
            title: Document title
            
        Returns:
            Complete LaTeX document as string
        """
        return r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{margin=1in}

\title{""" + title + r"""}

\begin{document}

""" + latex_content + r"""

\end{document}
"""
