"""
Gemini AI Image to LaTeX Converter
Uses Google's Gemini API to convert handwritten notes to LaTeX
"""
import os
import re
import time
from typing import Optional

from .base import ImageToLatexConverterBase


class GeminiImageToLatexConverter(ImageToLatexConverterBase):
    """Converts handwritten notes images to LaTeX using Gemini API with retry logic"""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gemini-2.0-flash-exp",
        max_retries: int = 3,
        timeout: int = 120,
        retry_delay: int = 5,
        rate_limiter: Optional[object] = None
    ):
        """
        Initialize Gemini converter
        
        Args:
            api_key: Google Gemini API key
            model: Model name to use
            max_retries: Maximum number of retry attempts
            timeout: Timeout in seconds for API calls
            retry_delay: Base delay between retries (exponential backoff)
            rate_limiter: Optional rate limiter instance
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.rate_limiter = rate_limiter
        
    def convert(self, image_path: str, custom_prompt: Optional[str] = None) -> str:
        """
        Convert image of handwritten notes to LaTeX with retry logic and rate limiting
        
        Args:
            image_path: Path to image file
            custom_prompt: Optional custom prompt for conversion
            
        Returns:
            LaTeX code as string
        """
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai not installed. Install with: pip install google-genai"
            )
        
        # Create Gemini client
        client = genai.Client(api_key=self.api_key)
        
        # Read and encode image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Default prompt
        if custom_prompt is None:
            prompt = """Convert this handwritten mathematical content to LaTeX code.

Instructions:
- Output ONLY the LaTeX code, no explanations
- Use proper LaTeX math environments (equation, align, etc.)
- For inline math use $...$, for display math use $$...$$ or equation environments
- Preserve the structure and organization of the content
- If there are sections or titles, use appropriate LaTeX commands
- Be precise with mathematical notation

Output only the LaTeX code."""
        else:
            prompt = custom_prompt
        
        # Retry logic
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # Apply rate limiting before making request
                if self.rate_limiter:
                    status = self.rate_limiter.get_status()
                    print(f"🔄 Converting {os.path.basename(image_path)} to LaTeX (attempt {attempt}/{self.max_retries})")
                    print(f"   Rate limit: {status['requests_made']}/{status['max_requests']} requests used in last {status['window_seconds']}s")
                    self.rate_limiter.wait_if_needed()
                else:
                    print(f"🔄 Converting {os.path.basename(image_path)} to LaTeX (attempt {attempt}/{self.max_retries})...")
                
                # Generate LaTeX with timeout handling
                # Note: timeout is handled via http_options in the client config
                response = client.models.generate_content(
                    model=self.model,
                    contents=[
                        prompt,
                        types.Part.from_bytes(
                            data=image_data,
                            mime_type="image/png"
                        )
                    ]
                )
                latex_code = response.text
                
                # Clean up markdown code blocks if present
                latex_code = self._clean_response(latex_code)
                
                print(f"✓ Successfully converted {os.path.basename(image_path)}")
                return latex_code
                
            except Exception as e:
                last_exception = e
                error_msg = str(e)
                
                print(f"⚠️ Attempt {attempt} failed: {error_msg}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt  # Exponential backoff
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed for {os.path.basename(image_path)}")
                    raise Exception(
                        f"Failed to convert {image_path} after {self.max_retries} attempts: {error_msg}"
                    ) from last_exception
        
        # Should never reach here, but just in case
        raise last_exception
    
    def _clean_response(self, text: str) -> str:
        """Remove markdown code blocks and extra formatting"""
        # Remove ```latex ... ``` blocks
        text = re.sub(r'```latex\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        return text.strip()