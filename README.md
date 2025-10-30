# AInotes - Modular PDF to LaTeX Converter

A modular, loosely-coupled PDF to LaTeX conversion pipeline with dependency injection and factory patterns.

## 🏗️ Architecture

The project uses **software engineering best practices** for maintainability and testability:

- **Dependency Injection**: Components receive dependencies through constructors
- **Abstract Base Classes**: Interfaces defined for all converters using Python ABC
- **Factory Pattern**: Dynamic creation of converter instances based on configuration
- **Configuration-Driven**: YAML/JSON configs to switch between implementations
- **Loose Coupling**: Easy to swap implementations (e.g., Gemini ↔ Dummy converter)

### Project Structure

```
AInotes/
├── src/
│   ├── converters/           # Converter implementations
│   │   ├── base.py          # Abstract base classes (interfaces)
│   │   ├── gemini_converter.py  # Gemini API implementation
│   │   ├── dummy_converter.py   # Testing implementation
│   │   └── pdf_converter.py     # PDF to image converter
│   ├── utils/               # Utility modules
│   │   ├── rate_limiter.py
│   │   ├── checkpoint_manager.py
│   │   ├── image_diff.py
│   │   └── latex_integrator.py
│   ├── pipeline/            # Main pipeline orchestration
│   │   └── pdf_latex_pipeline.py
│   ├── config_loader.py     # Configuration management
│   └── factory.py          # Factory for creating instances
├── config/                  # Configuration files
│   ├── config.test.yaml    # Testing config (dummy converter)
│   ├── config.prod.yaml    # Production config (Gemini API)
│   └── config.test.json    # Alternative JSON format
├── main.py                  # Entry point with DI setup
├── convert.py              # Legacy monolithic version
└── dummy_AI.py             # Legacy dummy converter
```

## 🚀 Quick Start

### Testing Mode (No API Key Required)

```bash
# Using YAML config
python main.py your_document.pdf --config config/config.test.yaml

# Or using JSON config
python main.py your_document.pdf --config config/config.test.json

# Or override converter on command line
python main.py your_document.pdf --converter dummy --output-dir test
```

### Production Mode (Requires Gemini API)

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Run with production config
python main.py your_document.pdf --config config/config.prod.yaml
```

## 🔧 Configuration

### Switching Between Converters

Edit `config/config.test.yaml` or `config/config.prod.yaml`:

```yaml
converters:
  image_to_latex:
    type: "dummy"  # Change to "gemini" for production
    # ... other settings
```

### Creating Custom Converters

1. **Extend the base class**:

```python
from src.converters.base import ImageToLatexConverterBase

class MyCustomConverter(ImageToLatexConverterBase):
    def convert(self, image_path: str, custom_prompt: Optional[str] = None) -> str:
        # Your implementation here
        return latex_code
```

2. **Register in factory** (`src/factory.py`):

```python
elif converter_type == 'custom':
    return MyCustomConverter(...)
```

3. **Update config**:

```yaml
converters:
  image_to_latex:
    type: "custom"
```

## 🧪 Testing vs Production

### Why Use Dummy Converter?

- **No API costs** during development
- **Fast iteration** (no network calls)
- **Reproducible results** for testing
- **Same interface** as real converter

### Switching to Production

Simply change configuration - **no code changes needed**:

```bash
# Testing
--config config/config.test.yaml

# Production  
--config config/config.prod.yaml
```

## 🎯 Benefits of This Architecture

### 1. **Loose Coupling**
- Components don't know about specific implementations
- Easy to swap converters without touching pipeline code

### 2. **Testability**
- Can inject mock objects for unit testing
- Dummy converter for integration testing

### 3. **Maintainability**
- Each component has single responsibility
- Changes to one converter don't affect others

### 4. **Extensibility**
- Add new converters by implementing the interface
- No need to modify existing code (Open/Closed Principle)

### 5. **Configuration-Driven**
- Switch implementations via config files
- No recompilation or code changes

## 📝 Example Usage

### Basic Usage

```python
from src.factory import ConverterFactory
from src.pipeline import PDFToLatexPipeline
from src.utils import CheckpointManager, LatexIntegrator

# Create converters using factory
pdf_converter = ConverterFactory.create_pdf_converter(dpi=300)
image_converter = ConverterFactory.create_image_to_latex_converter(
    converter_type='dummy'  # or 'gemini'
)

# Create pipeline with dependency injection
pipeline = PDFToLatexPipeline(
    pdf_converter=pdf_converter,
    image_converter=image_converter,
    checkpoint_manager=CheckpointManager(),
    latex_integrator=LatexIntegrator()
)

# Run conversion
result = pipeline.run('document.pdf', output_dir='output')
```

### Advanced: Custom Rate Limiter

```python
rate_limiter = ConverterFactory.create_rate_limiter(
    max_requests=5,
    time_window=60
)

image_converter = ConverterFactory.create_image_to_latex_converter(
    converter_type='gemini',
    api_key=os.getenv('GEMINI_API_KEY'),
    rate_limiter=rate_limiter
)
```

## 🔍 Command Line Options

```bash
python main.py PDF_PATH [options]

Required:
  PDF_PATH              Path to PDF file to convert

Optional:
  --config CONFIG       Config file path (auto-detects if omitted)
  --output-dir DIR      Output directory (overrides config)
  --converter TYPE      Converter type: 'gemini' or 'dummy' (overrides config)
  --no-resume          Start fresh instead of resuming from checkpoint
```

## 🌟 Key Features

- ✅ **Version Tracking** - Detects changed pages and re-processes only what's needed
- ✅ **Resume Capability** - Checkpoint system to resume after interruptions
- ✅ **Rate Limiting** - Configurable API rate limiting
- ✅ **Retry Logic** - Automatic retries with exponential backoff
- ✅ **Image Diff Detection** - Identifies changed pages automatically
- ✅ **Modular Architecture** - Clean separation of concerns
- ✅ **Dependency Injection** - Testable and maintainable code

## 📦 Dependencies

```bash
pip install pdf2image pillow scipy numpy google-generativeai python-dotenv pyyaml
```

## 🔄 Migration from Legacy Code

The old monolithic `convert.py` still works, but the new modular architecture offers:

- Better testability (dummy converter)
- Easier maintenance (single responsibility)
- Configuration-driven behavior
- Proper dependency injection

Gradually migrate by:
1. Use `main.py` for new workflows
2. Keep `convert.py` for legacy compatibility
3. Both use the same underlying conversion logic

---

**Made with ❤️ using modern software engineering practices**
