"""
LaTeX Error Fixer using AI
Takes LaTeX code with compilation errors and fixes them using an AI model
"""
import re
import time
from typing import Optional, List, Dict


class LatexErrorFixer:
    """Fixes LaTeX compilation errors using AI"""
    
    def __init__(
        self,
        converter_type: str = "gemini",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 5,
        rate_limiter: Optional[object] = None
    ):
        """
        Initialize LaTeX error fixer
        
        Args:
            converter_type: Type of AI converter ('gemini', 'openai', 'anthropic')
            api_key: API key for the AI service
            model: Model name to use
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries
            rate_limiter: Optional rate limiter instance
        """
        self.converter_type = converter_type.lower()
        self.api_key = api_key
        self.model = model or self._get_default_model()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.rate_limiter = rate_limiter
        
    def _get_default_model(self) -> str:
        """Get default model for the converter type"""
        defaults = {
            'gemini': 'gemini-2.0-flash-exp',
            'openai': 'gpt-4o',
            'anthropic': 'claude-3-5-sonnet-20241022'
        }
        return defaults.get(self.converter_type, 'gemini-2.0-flash-exp')
    
    def fix_errors(
        self,
        latex_code: str,
        errors: List[Dict[str, str]],
        max_fix_attempts: int = 2
    ) -> str:
        """
        Fix LaTeX compilation errors using AI
        
        Args:
            latex_code: The LaTeX code with errors
            errors: List of error dictionaries from LatexCompiler
            max_fix_attempts: Maximum number of fix attempts
            
        Returns:
            Fixed LaTeX code
        """
        if not errors:
            return latex_code
        
        print(f"\n🔧 Attempting to fix {len(errors)} compilation error(s)...")
        
        # Format errors for AI
        error_description = self._format_errors(errors)
        
        # Create prompt for AI
        prompt = f"""You are a LaTeX expert. The following LaTeX code has compilation errors.
Please fix ALL the errors and return ONLY the corrected LaTeX code.

{error_description}

ORIGINAL LATEX CODE:
```latex
{latex_code}
```

Instructions:
- Fix ALL compilation errors
- Preserve the original content and meaning
- Return ONLY the corrected LaTeX code
- Do NOT include explanations or comments
- Do NOT wrap the output in markdown code blocks
- Ensure all math environments are properly closed
- Check for missing packages, undefined commands, or syntax errors

CORRECTED LATEX CODE:"""

        # Call the appropriate AI service
        fixed_code = self._call_ai_service(prompt)
        
        return fixed_code
    
    def _format_errors(self, errors: List[Dict[str, str]]) -> str:
        """Format errors for AI prompt"""
        if not errors:
            return "No errors found."
        
        error_text = f"COMPILATION ERRORS ({len(errors)} errors):\n"
        for i, error in enumerate(errors, 1):
            error_text += f"\nError {i}:\n"
            error_text += f"  Line: {error.get('line', '?')}\n"
            error_text += f"  Message: {error.get('message', 'Unknown error')}\n"
        
        return error_text
    
    def _call_ai_service(self, prompt: str) -> str:
        """
        Call the AI service to fix the LaTeX code
        
        Args:
            prompt: The prompt with error description and code
            
        Returns:
            Fixed LaTeX code
        """
        if self.converter_type == 'gemini':
            return self._call_gemini(prompt)
        elif self.converter_type == 'openai':
            return self._call_openai(prompt)
        elif self.converter_type == 'anthropic':
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown converter type: {self.converter_type}")
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API to fix LaTeX"""
        try:
            from google import genai
        except ImportError:
            raise ImportError(
                "google-genai not installed. Install with: pip install google-genai"
            )
        
        client = genai.Client(api_key=self.api_key)
        
        # Retry logic
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                print(f"   Calling Gemini API (attempt {attempt}/{self.max_retries})...")
                
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt
                )
                
                fixed_code = response.text
                fixed_code = self._clean_response(fixed_code)
                
                print(f"✓ Successfully received fixed code from Gemini")
                return fixed_code
                
            except Exception as e:
                last_exception = e
                print(f"⚠️ Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed")
                    raise Exception(
                        f"Failed to fix LaTeX after {self.max_retries} attempts: {str(e)}"
                    ) from last_exception
        
        raise last_exception
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API to fix LaTeX"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai not installed. Install with: pip install openai"
            )
        
        client = OpenAI(api_key=self.api_key)
        
        # Retry logic
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                print(f"   Calling OpenAI API (attempt {attempt}/{self.max_retries})...")
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a LaTeX expert who fixes compilation errors."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                
                fixed_code = response.choices[0].message.content
                fixed_code = self._clean_response(fixed_code)
                
                print(f"✓ Successfully received fixed code from OpenAI")
                return fixed_code
                
            except Exception as e:
                last_exception = e
                print(f"⚠️ Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed")
                    raise Exception(
                        f"Failed to fix LaTeX after {self.max_retries} attempts: {str(e)}"
                    ) from last_exception
        
        raise last_exception
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API to fix LaTeX"""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic not installed. Install with: pip install anthropic"
            )
        
        client = Anthropic(api_key=self.api_key)
        
        # Retry logic
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self.rate_limiter:
                    self.rate_limiter.wait_if_needed()
                
                print(f"   Calling Anthropic API (attempt {attempt}/{self.max_retries})...")
                
                response = client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.3,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                fixed_code = response.content[0].text
                fixed_code = self._clean_response(fixed_code)
                
                print(f"✓ Successfully received fixed code from Anthropic")
                return fixed_code
                
            except Exception as e:
                last_exception = e
                print(f"⚠️ Attempt {attempt} failed: {str(e)}")
                
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * attempt
                    print(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"❌ All {self.max_retries} attempts failed")
                    raise Exception(
                        f"Failed to fix LaTeX after {self.max_retries} attempts: {str(e)}"
                    ) from last_exception
        
        raise last_exception
    
    def _clean_response(self, text: str) -> str:
        """Remove markdown code blocks and extra formatting"""
        # Remove ```latex ... ``` blocks
        text = re.sub(r'```latex\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Remove common AI response prefixes
        text = re.sub(r'^(Here is the corrected|Here\'s the fixed|Corrected).*?:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        return text.strip()
