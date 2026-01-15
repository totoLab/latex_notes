"""
LaTeX Integration utilities
Cleans and integrates raw LaTeX into main document
"""
import os
import re
from pathlib import Path
from typing import List, Optional


class LatexIntegrator:
    """Cleans and integrates raw LaTeX into main document"""
    
    def __init__(self, output_dir: str = "output/latex"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def clean_latex(self, raw_latex: str, remove_preamble: bool = True) -> str:
        """Clean raw LaTeX for integration"""
        if remove_preamble:
            # Remove document class and preamble
            raw_latex = re.sub(
                r'\\documentclass.*?\\begin\{document\}',
                '',
                raw_latex,
                flags=re.DOTALL
            )
            # Remove end document
            raw_latex = raw_latex.replace(r'\end{document}', '')
        
        # Clean up excessive whitespace
        raw_latex = re.sub(r'\n{3,}', '\n\n', raw_latex)
        
        return raw_latex.strip()
    
    def save_section(
        self,
        latex_content: str,
        filename: str,
        section_title: Optional[str] = None,
        wrap_in_section: bool = False
    ) -> str:
        """Save LaTeX content as a section file"""
        # Clean the content
        cleaned_latex = self.clean_latex(latex_content)
        
        # Optionally wrap in section
        if wrap_in_section and section_title:
            cleaned_latex = f"\\section{{{section_title}}}\n\n{cleaned_latex}"
        
        # Save to file
        output_path = os.path.join(self.output_dir, f"{filename}.tex")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_latex)
        
        print(f"✓ Saved LaTeX to {output_path}")
        return output_path
    
    def create_main_document(
        self,
        section_files: List[str],
        output_path: str = "output/main.tex",
        title: str = "Converted Notes",
        author: str = ""
    ) -> str:
        """Create a main LaTeX document that includes all sections"""
        # Create document structure
        doc_content = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{geometry}
\usepackage{arydshln}
\geometry{margin=1in}

"""
        if title:
            doc_content += f"\\title{{{title}}}\n"
        if author:
            doc_content += f"\\author{{{author}}}\n"
        
        doc_content += r"""
\begin{document}

"""
        if title:
            doc_content += r"\maketitle" + "\n\n"
        
        # Add input statements for each section
        for section_file in section_files:
            # Use relative path from main document
            rel_path = os.path.relpath(section_file, os.path.dirname(output_path))
            # Remove .tex extension for \input
            rel_path_no_ext = os.path.splitext(rel_path)[0]
            doc_content += f"\\input{{{rel_path_no_ext}}}\n\n"
        
        doc_content += r"\end{document}"
        
        # Save main document
        Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✓ Created main document at {output_path}")
        return output_path
    
    def append_section_to_main(
        self,
        section_file: str,
        main_doc_path: str,
        title: str = "Converted Notes",
        author: str = ""
    ) -> str:
        """
        Append a section to an existing main document, or create it if it doesn't exist
        
        Args:
            section_file: Path to the section file to append
            main_doc_path: Path to the main document
            title: Document title (used if creating new document)
            author: Document author (used if creating new document)
            
        Returns:
            Path to the updated main document
        """
        # Check if main document exists
        if not os.path.exists(main_doc_path):
            # Create initial document structure
            doc_content = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}
\usepackage{graphicx}
\usepackage{cancel}
\usepackage{tikz}
\usepackage{arydshln}
\usepackage{geometry}
\geometry{margin=1in}

"""
            if title:
                doc_content += f"\\title{{{title}}}\n"
            if author:
                doc_content += f"\\author{{{author}}}\n"
            
            doc_content += r"""
\begin{document}

"""
            if title:
                doc_content += r"\maketitle" + "\n\n"
            
            doc_content += r"\end{document}"
            
            # Ensure directory exists
            Path(os.path.dirname(main_doc_path)).mkdir(parents=True, exist_ok=True)
            
            with open(main_doc_path, 'w', encoding='utf-8') as f:
                f.write(doc_content)
        
        # Read current content
        with open(main_doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the position of \end{document}
        end_doc_pos = content.rfind(r'\end{document}')
        
        if end_doc_pos == -1:
            raise ValueError(f"Invalid main document: missing \\end{{document}} in {main_doc_path}")
        
        # Calculate relative path from main document to section file
        rel_path = os.path.relpath(section_file, os.path.dirname(main_doc_path))
        rel_path_no_ext = os.path.splitext(rel_path)[0]
        
        # Check if this section is already included
        input_statement = f"\\input{{{rel_path_no_ext}}}"
        if input_statement in content:
            # Section already included, don't duplicate
            return main_doc_path
        
        # Insert the new \input statement before \end{document}
        new_content = (
            content[:end_doc_pos] +
            f"{input_statement}\n\n" +
            content[end_doc_pos:]
        )
        
        # Write updated content
        with open(main_doc_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return main_doc_path
