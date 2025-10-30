"""
Factory for creating converter instances based on configuration
Implements dependency injection pattern
"""
from typing import Optional
from .converters.base import ImageToLatexConverterBase, PDFToImageConverterBase
from .converters.gemini_converter import GeminiImageToLatexConverter
from .converters.dummy_converter import DummyImageToLatexConverter
from .converters.pdf_converter import PDFToImageConverter
from .utils.rate_limiter import RateLimiter


class ConverterFactory:
    """Factory for creating converter instances"""
    
    @staticmethod
    def create_image_to_latex_converter(
        converter_type: str,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash-exp",
        max_retries: int = 3,
        timeout: int = 120,
        retry_delay: int = 5,
        rate_limiter: Optional[RateLimiter] = None
    ) -> ImageToLatexConverterBase:
        """
        Create an image to LaTeX converter based on type
        
        Args:
            converter_type: Type of converter ('gemini' or 'dummy')
            api_key: API key (required for gemini)
            model: Model name for gemini
            max_retries: Max retry attempts
            timeout: Timeout in seconds
            retry_delay: Delay between retries
            rate_limiter: Optional rate limiter instance
            
        Returns:
            ImageToLatexConverterBase instance
        """
        converter_type = converter_type.lower()
        
        if converter_type == 'dummy':
            print("🧪 Using DummyImageToLatexConverter (testing mode)")
            return DummyImageToLatexConverter(
                api_key=api_key or "dummy_key",
                model=model,
                max_retries=max_retries,
                timeout=timeout,
                retry_delay=retry_delay,
                rate_limiter=rate_limiter
            )
        elif converter_type == 'gemini':
            if not api_key:
                raise ValueError("API key required for Gemini converter")
            print(f"🤖 Using GeminiImageToLatexConverter (model: {model})")
            return GeminiImageToLatexConverter(
                api_key=api_key,
                model=model,
                max_retries=max_retries,
                timeout=timeout,
                retry_delay=retry_delay,
                rate_limiter=rate_limiter
            )
        else:
            raise ValueError(
                f"Unknown converter type: {converter_type}. "
                f"Available types: 'gemini', 'dummy'"
            )
    
    @staticmethod
    def create_pdf_converter(
        dpi: int = 300,
        enable_diff_check: bool = True
    ) -> PDFToImageConverterBase:
        """
        Create a PDF to image converter
        
        Args:
            dpi: DPI resolution for images
            enable_diff_check: Whether to enable difference checking
            
        Returns:
            PDFToImageConverterBase instance
        """
        return PDFToImageConverter(
            dpi=dpi,
            enable_diff_check=enable_diff_check
        )
    
    @staticmethod
    def create_rate_limiter(
        max_requests: int = 2,
        time_window: int = 60
    ) -> RateLimiter:
        """
        Create a rate limiter instance
        
        Args:
            max_requests: Maximum requests allowed
            time_window: Time window in seconds
            
        Returns:
            RateLimiter instance
        """
        return RateLimiter(
            max_requests=max_requests,
            time_window=time_window
        )
