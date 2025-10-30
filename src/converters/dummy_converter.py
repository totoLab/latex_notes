"""
Dummy Image to LaTeX Converter for testing without API
Always returns Lorem Ipsum in LaTeX format
"""
import os
import time
import re
from typing import Optional

from .base import ImageToLatexConverterBase


class DummyImageToLatexConverter(ImageToLatexConverterBase):
    """Dummy converter that returns Lorem Ipsum LaTeX - for testing only"""
    
    def __init__(
        self, 
        api_key: str = "dummy_key", 
        model: str = "dummy-model",
        max_retries: int = 3,
        timeout: int = 120,
        retry_delay: int = 5,
        rate_limiter: Optional[object] = None
    ):
        """Initialize dummy converter - accepts same params as real converter for compatibility"""
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.rate_limiter = rate_limiter
        
        # Different Lorem Ipsum variants for variety
        self.lorem_variants = [
            r"""
\subsection{Lorem Ipsum Dolor}

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

\begin{equation}
    E = mc^2
\end{equation}

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

\begin{align}
    a^2 + b^2 &= c^2 \\
    x &= \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}
\end{align}

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
""",
            r"""
\subsection{Mathematical Expressions}

Consider the following integral:

\begin{equation}
    \int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}
\end{equation}

Lorem ipsum dolor sit amet, where $\alpha + \beta = \gamma$ represents the fundamental relationship.

\begin{itemize}
    \item First principle: $f(x) = x^2 + 2x + 1$
    \item Second principle: $\nabla \cdot \vec{E} = \frac{\rho}{\epsilon_0}$
    \item Third principle: $\lim_{n \to \infty} \sum_{i=1}^{n} \frac{1}{i} = \infty$
\end{itemize}

Excepteur sint occaecat cupidatat non proident.
""",
            r"""
\subsection{Theoretical Framework}

Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium.

\begin{theorem}
For all $n \in \mathbb{N}$, we have:
$$\sum_{k=1}^{n} k = \frac{n(n+1)}{2}$$
\end{theorem}

\begin{proof}
Lorem ipsum dolor sit amet, using mathematical induction on $n$.
\end{proof}

The matrix representation is given by:

\begin{equation}
    \mathbf{A} = \begin{pmatrix}
        a_{11} & a_{12} & a_{13} \\
        a_{21} & a_{22} & a_{23} \\
        a_{31} & a_{32} & a_{33}
    \end{pmatrix}
\end{equation}

At vero eos et accusamus et iusto odio dignissimos.
""",
            r"""
\subsection{Advanced Concepts}

Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit.

Let $X$ be a random variable with probability density function:

\begin{equation}
    f_X(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}
\end{equation}

\begin{enumerate}
    \item Property 1: $\mathbb{E}[X] = \mu$
    \item Property 2: $\text{Var}(X) = \sigma^2$
    \item Property 3: $P(X \leq x) = \Phi\left(\frac{x-\mu}{\sigma}\right)$
\end{enumerate}

Temporibus autem quibusdam et aut officiis debitis.

\begin{align*}
    \nabla \times \vec{B} &= \mu_0 \vec{J} + \mu_0 \epsilon_0 \frac{\partial \vec{E}}{\partial t} \\
    \nabla \times \vec{E} &= -\frac{\partial \vec{B}}{\partial t}
\end{align*}
""",
            r"""
\subsection{Derivations and Results}

Quis autem vel eum iure reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur.

The fundamental theorem states:

\begin{equation}
    \int_a^b f'(x)\,dx = f(b) - f(a)
\end{equation}

Consider the series expansion:

$$f(x) = \sum_{n=0}^{\infty} \frac{f^{(n)}(a)}{n!}(x-a)^n$$

\textbf{Corollary:} Lorem ipsum dolor sit amet, where:
\begin{itemize}
    \item $\sin(x) = x - \frac{x^3}{3!} + \frac{x^5}{5!} - \cdots$
    \item $\cos(x) = 1 - \frac{x^2}{2!} + \frac{x^4}{4!} - \cdots$
    \item $e^x = 1 + x + \frac{x^2}{2!} + \frac{x^3}{3!} + \cdots$
\end{itemize}

Vel illum qui dolorem eum fugiat quo voluptas nulla pariatur.
"""
        ]
    
    def convert(self, image_path: str, custom_prompt: Optional[str] = None) -> str:
        """
        Dummy conversion - returns Lorem Ipsum LaTeX
        
        Args:
            image_path: Path to image file (not actually used)
            custom_prompt: Optional custom prompt (ignored)
            
        Returns:
            Lorem Ipsum LaTeX code as string
        """
        # Apply rate limiting if available
        if self.rate_limiter:
            status = self.rate_limiter.get_status()
            print(f"🔄 [DUMMY] Converting {os.path.basename(image_path)} to LaTeX")
            print(f"   Rate limit: {status['requests_made']}/{status['max_requests']} requests used in last {status['window_seconds']}s")
            self.rate_limiter.wait_if_needed()
        else:
            print(f"🔄 [DUMMY] Converting {os.path.basename(image_path)} to LaTeX...")
        
        # Simulate processing time (0.5-2 seconds)
        time.sleep(0.5)
        
        # Get a Lorem Ipsum variant based on image path (for consistency)
        # Extract page number from filename if possible
        page_match = re.search(r'page(\d+)', image_path)
        if page_match:
            page_num = int(page_match.group(1))
            variant_index = (page_num - 1) % len(self.lorem_variants)
        else:
            variant_index = 0
        
        latex_code = self.lorem_variants[variant_index]
        
        print(f"✓ [DUMMY] Successfully converted {os.path.basename(image_path)}")
        return latex_code
