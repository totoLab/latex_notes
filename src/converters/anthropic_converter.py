"""
Anthropic Claude Image to LaTeX Converter
Uses Anthropic's Claude models (Haiku 4.5 / Sonnet 4.5) to convert handwritten notes to LaTeX
"""
import os
import re
import time
import base64
from typing import Optional

from .base import ImageToLatexConverterBase


class AnthropicImageToLatexConverter(ImageToLatexConverterBase):
    """Converts handwritten notes images to LaTeX using Anthropic Claude with retry logic"""
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "claude-haiku-4-5-20251001",
        max_retries: int = 3,
        timeout: int = 120,
        retry_delay: int = 5,
        rate_limiter: Optional[object] = None
    ):
        """
        Initialize Anthropic converter
        
        Args:
            api_key: Anthropic API key
            model: Model name to use (claude-haiku-4-5-20251001 or claude-sonnet-4-5-20250929)
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
            import anthropic
            from anthropic import AuthenticationError, RateLimitError
        except ImportError:
            raise ImportError(
                "anthropic not installed. Install with: pip install anthropic"
            )
        
        # Create Anthropic client
        client = anthropic.Anthropic(
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        # Read and encode image to base64
        with open(image_path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        # Determine image mime type from file extension
        ext = os.path.splitext(image_path)[1].lower()
        mime_type_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_type_map.get(ext, 'image/png')
        
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
                
                # Create message with vision
                message = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type,
                                        "data": image_data,
                                    },
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ],
                        }
                    ],
                )
                
                # Extract text from response
                latex_code = message.content[0].text
                
                # Clean up markdown code blocks if present
                latex_code = self._clean_response(latex_code)
                
                print(f"✓ Successfully converted {os.path.basename(image_path)}")
                return latex_code
                
            except AuthenticationError as e:
                print(f"❌ API key invalid: {e}")
                raise
                
            except RateLimitError as e:
                last_exception = e
                print(f"⚠️ Rate limit hit on attempt {attempt}: {e}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed for {os.path.basename(image_path)}")
                    raise Exception(
                        f"Failed to convert {image_path} after {self.max_retries} attempts: Rate limit exceeded"
                    ) from last_exception
                    
            except anthropic.APITimeoutError as e:
                last_exception = e
                print(f"⚠️ Request timeout on attempt {attempt}: {e}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed for {os.path.basename(image_path)}")
                    raise Exception(
                        f"Failed to convert {image_path} after {self.max_retries} attempts: Timeout"
                    ) from last_exception
                    
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
        if text is None:
            return ""
        
        # Remove ```latex ... ``` blocks
        text = re.sub(r'```latex\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        return text.strip()