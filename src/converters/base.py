"""
Abstract base classes for converters to ensure loose coupling
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple


class PDFToImageConverterBase(ABC):
    """Abstract base class for PDF to Image converters"""
    
    @abstractmethod
    def convert(
        self, 
        pdf_path: str, 
        output_dir: str = "output/images",
        checkpoint: Optional[Dict] = None
    ) -> Tuple[List[str], Dict[int, int]]:
        """
        Convert PDF to images
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images
            checkpoint: Current checkpoint data for version tracking
            
        Returns:
            Tuple of (list of image file paths, dict mapping page_num -> image_version)
        """
        pass


class ImageToLatexConverterBase(ABC):
    """Abstract base class for Image to LaTeX converters"""
    
    @abstractmethod
    def convert(self, image_path: str, custom_prompt: Optional[str] = None) -> str:
        """
        Convert image to LaTeX code
        
        Args:
            image_path: Path to image file
            custom_prompt: Optional custom prompt for conversion
            
        Returns:
            LaTeX code as string
        """
        pass
    
    def _clean_response(self, text: str) -> str:
        """
        Optional method to clean/post-process response
        Can be overridden by subclasses
        """
        return text.strip()
