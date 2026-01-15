"""
LaTeX Compiler utility
Compiles LaTeX documents and captures errors
"""
import os
import subprocess
import re
from pathlib import Path
from typing import Tuple, List, Optional, Dict


class LatexCompiler:
    """Compiles LaTeX documents and extracts compilation errors"""
    
    def __init__(self, compiler: str = "xelatex", output_dir: Optional[str] = None):
        """
        Initialize LaTeX compiler
        
        Args:
            compiler: LaTeX compiler to use (xelatex, pdflatex, lualatex)
            output_dir: Directory where compilation should happen
        """
        self.compiler = compiler
        self.output_dir = output_dir
    
    def compile(self, tex_file: str, clean_aux: bool = True) -> Tuple[bool, str, List[Dict[str, str]]]:
        """
        Compile a LaTeX document
        
        Args:
            tex_file: Path to the .tex file to compile
            clean_aux: Whether to clean auxiliary files after compilation
            
        Returns:
            Tuple of (success, output, errors)
            - success: Whether compilation succeeded
            - output: Full compilation output
            - errors: List of error dictionaries with 'line', 'message', 'context'
        """
        tex_path = Path(tex_file)
        if not tex_path.exists():
            return False, f"File not found: {tex_file}", [{"line": "N/A", "message": f"File not found: {tex_file}", "context": ""}]
        
        # Determine working directory
        work_dir = self.output_dir or tex_path.parent
        
        # Build compilation command
        # Use -interaction=nonstopmode to not stop on errors
        # Use -halt-on-error to stop at first error but still get output
        cmd = [
            self.compiler,
            "-interaction=nonstopmode",
            "-file-line-error",
            tex_path.name
        ]
        
        try:
            print(f"🔨 Compiling {tex_path.name} with {self.compiler}...")
            
            # Run compilation
            result = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            output = result.stdout + result.stderr
            
            # Parse errors from output
            errors = self._parse_errors(output, tex_path.name)
            
            # Check if compilation succeeded
            success = result.returncode == 0 and len(errors) == 0
            
            if success:
                print(f"✅ Compilation successful!")
            else:
                print(f"❌ Compilation failed with {len(errors)} error(s)")
            
            # Clean auxiliary files if requested
            if clean_aux and success:
                self._clean_aux_files(work_dir, tex_path.stem)
            
            return success, output, errors
            
        except subprocess.TimeoutExpired:
            error_msg = "Compilation timeout (>60s)"
            print(f"❌ {error_msg}")
            return False, error_msg, [{"line": "N/A", "message": error_msg, "context": ""}]
        except Exception as e:
            error_msg = f"Compilation error: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg, [{"line": "N/A", "message": str(e), "context": ""}]
    
    def _parse_errors(self, output: str, filename: str) -> List[Dict[str, str]]:
        """
        Parse LaTeX errors from compilation output
        
        Args:
            output: Compilation output text
            filename: Name of the tex file being compiled
            
        Returns:
            List of error dictionaries
        """
        errors = []
        
        # Pattern for file-line-error format: ./file.tex:123: Error message
        error_pattern = re.compile(
            r'(?:\./)?' + re.escape(filename) + r':(\d+):\s*(.*?)(?:\n|$)',
            re.MULTILINE
        )
        
        for match in error_pattern.finditer(output):
            line_num = match.group(1)
            message = match.group(2).strip()
            
            # Skip some non-critical messages
            if any(skip in message.lower() for skip in ['warning', 'overfull', 'underfull']):
                continue
            
            errors.append({
                "line": line_num,
                "message": message,
                "context": self._extract_context(output, match.start())
            })
        
        # Also look for general errors without line numbers
        general_error_pattern = re.compile(r'!\s*(.*?)(?:\n|$)', re.MULTILINE)
        for match in general_error_pattern.finditer(output):
            error_msg = match.group(1).strip()
            
            # Avoid duplicates
            if not any(err['message'] == error_msg for err in errors):
                errors.append({
                    "line": "?",
                    "message": error_msg,
                    "context": self._extract_context(output, match.start())
                })
        
        return errors
    
    def _extract_context(self, output: str, error_pos: int, context_lines: int = 3) -> str:
        """
        Extract context around an error position in the output
        
        Args:
            output: Full compilation output
            error_pos: Position of error in output
            context_lines: Number of lines to include before/after
            
        Returns:
            Context string
        """
        lines = output[:error_pos + 500].split('\n')
        # Get last few lines before error
        context = '\n'.join(lines[-context_lines-1:])
        return context.strip()
    
    def _clean_aux_files(self, directory: Path, base_name: str):
        """
        Clean auxiliary files generated during compilation
        
        Args:
            directory: Directory containing the files
            base_name: Base name of the tex file (without extension)
        """
        aux_extensions = ['.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk', '.synctex.gz']
        
        for ext in aux_extensions:
            aux_file = directory / f"{base_name}{ext}"
            if aux_file.exists():
                aux_file.unlink()
    
    def format_errors_for_ai(self, errors: List[Dict[str, str]], latex_code: str) -> str:
        """
        Format errors in a way that's easy for AI to understand and fix
        
        Args:
            errors: List of error dictionaries
            latex_code: The LaTeX code that failed to compile
            
        Returns:
            Formatted error description
        """
        if not errors:
            return "No errors found."
        
        error_description = f"Found {len(errors)} compilation error(s):\n\n"
        
        for i, error in enumerate(errors, 1):
            error_description += f"Error {i}:\n"
            error_description += f"  Line: {error['line']}\n"
            error_description += f"  Message: {error['message']}\n"
            if error['context']:
                error_description += f"  Context:\n{error['context']}\n"
            error_description += "\n"
        
        # Add the problematic code
        error_description += "\nProblematic LaTeX code:\n"
        error_description += "```latex\n"
        error_description += latex_code
        error_description += "\n```\n"
        
        return error_description
