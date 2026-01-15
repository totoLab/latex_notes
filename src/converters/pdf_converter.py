"""
PDF to Image Converter
Converts PDF pages to images with optional change detection
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from PIL import Image

from .base import PDFToImageConverterBase
from ..utils.image_diff import ImageDiff


class PDFToImageConverter(PDFToImageConverterBase):
    """Converts PDF pages to images with optional re-extraction for changed pages"""
    
    def __init__(self, dpi: int = 300, enable_diff_check: bool = True):
        """
        Initialize PDF converter
        
        Args:
            dpi: DPI resolution for image extraction
            enable_diff_check: Whether to detect changes in existing images
        """
        self.dpi = dpi
        self.enable_diff_check = enable_diff_check
        
    def convert(
        self, 
        pdf_path: str, 
        output_dir: str = "output/images",
        checkpoint: Optional[Dict] = None
    ) -> Tuple[List[str], Dict[int, int]]:
        """
        Convert PDF to images with version tracking
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images
            checkpoint: Current checkpoint data for version tracking
            
        Returns:
            Tuple of (list of image file paths, dict mapping page_num -> image_version)
        """
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image not installed. Install with: pip install pdf2image\n"
                "Also requires poppler: https://pdf2image.readthedocs.io/en/latest/installation.html"
            )
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save images and track versions, processing one page at a time
        image_paths = []
        image_versions = {}  # page_num -> version
        pdf_name = Path(pdf_path).stem

        # Get number of pages in PDF
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
        except ImportError:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")

        for i in range(1, num_pages + 1):
            images = convert_from_path(pdf_path, dpi=self.dpi, first_page=i, last_page=i)
            if not images:
                continue
            image = images[0]
            image_path = os.path.join(output_dir, f"{pdf_name}_page{i}.png")

            # Get current version from checkpoint
            current_version = 0
            if checkpoint and 'pages' in checkpoint:
                for page_entry in checkpoint['pages']:
                    if page_entry['page'] == i:
                        current_version = page_entry.get('image_version', 0)
                        break

            # Check if image already exists and if diff checking is enabled
            if self.enable_diff_check and os.path.exists(image_path):
                # Load existing image
                existing_image = Image.open(image_path)

                # Compare images using ImageDiff
                diff_checker = ImageDiff(existing_image, image)
                clusters = diff_checker.run()

                if len(clusters) > 2:
                    # Image has changed - increment version
                    new_version = current_version + 1
                    print(f"⚠️ Page {i} has {len(clusters)} changes detected - updating (v{current_version} → v{new_version})")

                    # Save the new image
                    image.save(image_path, 'PNG')
                    print(f"✓ Updated page {i} to version {new_version}")
                    image_paths.append(image_path)
                    image_versions[i] = new_version
                else:
                    # Image unchanged - keep current version
                    if clusters:
                        print(f"✓ Page {i} has {len(clusters)} minor changes - keeping version {current_version}")
                    else:
                        print(f"✓ Page {i} unchanged - version {current_version}")
                    image_paths.append(image_path)
                    image_versions[i] = current_version
                # Explicitly close and delete existing_image to free memory
                existing_image.close()
                del existing_image
            else:
                # New image - version 1
                new_version = 1
                image.save(image_path, 'PNG')
                print(f"✓ Saved page {i} as version {new_version}")
                image_paths.append(image_path)
                image_versions[i] = new_version

            # Explicitly close and delete image to free memory
            image.close()
            del image

        return image_paths, image_versions
