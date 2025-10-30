"""
Complete PDF to LaTeX conversion pipeline with dependency injection
"""
import os
import time
import traceback
from typing import Optional, Dict

from ..converters.base import PDFToImageConverterBase, ImageToLatexConverterBase
from ..utils import CheckpointManager, LatexIntegrator


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
        latex_integrator: Optional[LatexIntegrator] = None
    ):
        """
        Initialize pipeline with injected dependencies
        
        Args:
            pdf_converter: PDF to image converter instance
            image_converter: Image to LaTeX converter instance
            checkpoint_manager: Optional checkpoint manager (creates default if None)
            latex_integrator: Optional LaTeX integrator (creates default if None)
        """
        self.pdf_converter = pdf_converter
        self.image_converter = image_converter
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.latex_integrator = latex_integrator or LatexIntegrator()
    
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
                print(f"⏭️ Skipping page {i}/{len(images)} (up to date)")
                continue
            
            try:
                page_entry = self.checkpoint_manager.get_page_entry(checkpoint, i)
                current_img_version = page_entry['image_version'] if page_entry else 1
                
                print(f"\n📄 Processing page {i}/{len(images)} (image v{current_img_version})...")
                
                # Convert image to LaTeX using injected converter
                latex_code = self.image_converter.convert(image_path)
                
                # Save as section
                section_file = self.latex_integrator.save_section(
                    latex_code,
                    filename=f"{section_prefix}_page{i}",
                    section_title=f"Page {i}",
                    wrap_in_section=True
                )
                
                latex_sections.append(section_file)
                
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
        
        # Stage 3: Create main document
        main_doc_path = None
        if create_main_doc:
            print("Stage 3: Creating main document...")
            main_doc_path = os.path.join(output_dir, "main.tex")
            self.latex_integrator.create_main_document(
                latex_sections,
                output_path=main_doc_path,
                title=doc_title
            )
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
