# AInotes: PDF to LaTeX Converter

AInotes is a powerful tool that converts PDF documents, especially those with handwritten notes, into clean, compilable LaTeX code. It uses AI to understand the content and structure of your documents, and can even automatically fix compilation errors.

## Quick Start

Here are a few ways to get started:

### 1. Simple Conversion (No API Key Needed)

This uses a dummy converter for testing and is great for seeing how the tool works.

```bash
python main.py your_document.pdf --config config/config.test.yaml
```

### 2. Production Conversion (API Key Required)

For real conversions, you'll need an API key from a provider like Google (Gemini), OpenAI, or Anthropic.

```bash
# Set your API key as an environment variable
export GEMINI_API_KEY="your-api-key-here"

# Run the conversion with the production configuration
python main.py your_document.pdf --config config/prod.yaml
```
This will convert your PDF and automatically attempt to fix any LaTeX compilation errors.

### 3. Using Workspaces

Workspaces help you manage multiple projects.

```bash
# Create a new workspace for your notes
python main.py workspace create my-notes-project /path/to/your/notes.pdf

# Run the conversion on your workspace
python main.py convert --workspace my-notes-project
```

That's it! The output will be saved in a directory (e.g., `output/` or `workspaces/my-notes-project/`) containing the generated `.tex` files.
