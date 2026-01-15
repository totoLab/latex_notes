"""
PDF to Image Converter
Converts PDF pages to images with optional change detection
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from PIL import Image
import concurrent.futures
from threading import Lock

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
        
    def get_pdf_pages(self, pdf_path: str):
        """
        Returns an iterator over page numbers (1-based) for the given PDF file.
        Caches the result in the object for future reference.
        """
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(pdf_path)
            num_pages = len(reader.pages)
        except ImportError:
            raise ImportError("PyPDF2 not installed. Install with: pip install PyPDF2")
        self._last_pdf_path = pdf_path
        self._last_pdf_pages = list(range(1, num_pages + 1))
        # Explicitly release the reader object to help unload the PDF from memory
        del reader
        return iter(self._last_pdf_pages)
        
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

        # Thread-safe containers
        lock = Lock()
        image_paths_shared = []
        image_versions_shared = {}

        def process_page(i):
            images = convert_from_path(pdf_path, dpi=self.dpi, first_page=i, last_page=i)
            if not images:
                return
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
                existing_image = Image.open(image_path)
                diff_checker = ImageDiff(existing_image, image)
                clusters = diff_checker.run()
                if len(clusters) > 2:
                    new_version = current_version + 1
                    print(f"⚠️ Page {i} has {len(clusters)} changes detected - updating (v{current_version} → v{new_version})")
                    image.save(image_path, 'PNG')
                    print(f"✓ Updated page {i} to version {new_version}")
                    with lock:
                        image_paths_shared.append(image_path)
                        image_versions_shared[i] = new_version
                else:
                    if clusters:
                        print(f"✓ Page {i} has {len(clusters)} minor changes - keeping version {current_version}")
                    else:
                        print(f"✓ Page {i} unchanged - version {current_version}")
                    with lock:
                        image_paths_shared.append(image_path)
                        image_versions_shared[i] = current_version
                existing_image.close()
                del existing_image
            else:
                new_version = 1
                image.save(image_path, 'PNG')
                print(f"✓ Saved page {i} as version {new_version}")
                with lock:
                    image_paths_shared.append(image_path)
                    image_versions_shared[i] = new_version
            image.close()
            del image

        # Use ThreadPoolExecutor to process pages in parallel
        max_workers = min(4, num_pages)  # Limit number of threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(process_page, range(1, num_pages + 1))
        # Sort image_paths by page number
        image_paths_sorted = [os.path.join(output_dir, f"{pdf_name}_page{i}.png") for i in sorted(image_versions_shared.keys())]
        image_versions_sorted = {i: image_versions_shared[i] for i in sorted(image_versions_shared.keys())}
        return image_paths_sorted, image_versions_sorted
