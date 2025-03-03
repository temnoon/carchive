# Carchive Enhanced Rendering System

This module provides a robust rendering system for Carchive content, capable of handling:

- Markdown content with enhanced features
- LaTeX equations with repair for common corruption
- Image embedding from local files and the media database
- Multiple output formats (HTML, PDF)
- Customizable templates

## Architecture

The enhanced rendering system follows an object-oriented design with these key components:

1. **ContentRenderer** (base_renderer.py)
   - Abstract base class that defines the common interface
   - Methods for rendering text, collections, conversations, and search results

2. **MarkdownRenderer** (markdown_renderer.py)
   - Handles parsing and processing of markdown content
   - LaTeX repair functionality to fix common corruption patterns
   - Image reference processing (local files and media database)

3. **TemplateEngine** (template_engine.py)
   - Jinja2-based template system for creating consistent output
   - Handles template discovery and rendering
   - Manages the templates directory

4. **HTMLRenderer** (html_renderer.py)
   - Implementation of ContentRenderer for HTML output
   - Uses MarkdownRenderer and TemplateEngine
   - Formats content with role-based styles and MathJax

5. **PDFRenderer** (pdf_renderer.py)
   - Implementation of ContentRenderer for PDF output
   - Uses HTMLRenderer and WeasyPrint
   - Applies PDF-specific styling and page numbering

## Templates

The system includes several built-in templates in the `templates/` directory:

- `default.html` - Clean design with role-based styling
- `academic.html` - Scholarly style for research content

Custom templates can be added to the templates directory and used by name.

## Usage

### Command Line

The rendering functionality is exposed through the CLI in `render_cli.py`:

```bash
# Render a conversation to HTML
poetry run carchive render conversation <conversation-id> --output-file output.html

# Render a collection to PDF
poetry run carchive render collection "Collection Name" output.pdf --format pdf

# Combine multiple collections
poetry run carchive render combined "Collection1" "Collection2" combined.html

# List available templates
poetry run carchive render templates
```

### Python API

```python
from carchive.rendering import HTMLRenderer, PDFRenderer, MarkdownRenderer

# Render markdown to HTML
markdown_renderer = MarkdownRenderer()
html_content = markdown_renderer.render("# Title\n\nContent with $LaTeX$ equations")

# Render a conversation to HTML
html_renderer = HTMLRenderer()
html_renderer.render_conversation(
    conversation_id="conv-id",
    output_path="output.html",
    template="academic"
)

# Render a collection to PDF
pdf_renderer = PDFRenderer()
pdf_renderer.render_collection(
    collection_name="Research Notes",
    output_path="research.pdf"
)
```

## LaTeX Support

The system uses MathJax for LaTeX rendering with these features:

- Support for both inline ($...$) and display ($$...$$) math
- Automatic repair of common corruption patterns
- Standardization of delimiters for consistent rendering

## Image Handling

Images are handled through different reference types:

- Local file references: `![Alt text](file:path/to/image.jpg)`
- Media database references: `![Alt text](media:uuid-here)`
- Standard URLs: `![Alt text](https://example.com/image.jpg)`

## Extension

To create a new output format, implement a new class that extends `ContentRenderer`.

See the comprehensive guide in `docs/enhanced_rendering_guide.md` for more details.