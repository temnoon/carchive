# Enhanced Rendering System for Carchive

This PR implements a comprehensive rendering system for Carchive that builds on the existing rendering capabilities and adds several key enhancements:

## New Features

1. **Unified Object-Oriented Architecture**
   - Introduces a clean object-oriented design with base classes and specialized renderers
   - Provides a consistent interface for rendering different content types
   - Easy to extend for new formats or specialized rendering needs

2. **Enhanced Markdown Handling**
   - LaTeX repair for common corruption patterns
   - Intelligent handling of different LaTeX delimiters
   - Robust image reference processing from multiple sources

3. **Multiple Output Formats**
   - HTML output with customizable templates
   - PDF generation via WeasyPrint (with graceful fallback if not available)
   - Consistent styling across formats

4. **Template-Based Rendering**
   - Jinja2-based templating system
   - Multiple built-in templates (default, academic)
   - Easy to create new templates or customize existing ones

5. **Improved CLI Commands**
   - New commands for rendering collections, conversations, and combined content
   - Support for different output formats and template selection
   - Command to list available templates and formats

## Technical Details

The system consists of several key components:

1. **ContentRenderer** (base_renderer.py)
   - Abstract base class defining the rendering interface
   - Methods for rendering text, collections, conversations, and search results

2. **MarkdownRenderer** (markdown_renderer.py)
   - Handles LaTeX repair and image processing
   - Processes embedded images from local files and the media database
   - Safely handles database errors and missing references

3. **TemplateEngine** (template_engine.py)
   - Manages templates directory and template loading
   - Provides consistent rendering of templates with context
   - Creates default templates if they don't exist

4. **HTMLRenderer** (html_renderer.py)
   - Renders content to HTML with proper styling
   - Handles message roles and metadata
   - Works with database content from collections and conversations

5. **PDFRenderer** (pdf_renderer.py)
   - Converts HTML to PDF using WeasyPrint
   - Adds PDF-specific styling and page numbering
   - Handles WeasyPrint availability gracefully

## Templates

Two templates are included:

1. **default.html** - Clean, modern design suitable for most content
2. **academic.html** - More formal design with enhanced typography for research content

## Testing

Unit tests are included to verify:
- LaTeX rendering and repair
- Markdown processing
- HTML and PDF output (when available)

Tests run without database access for reliability and independence.

## Documentation

Comprehensive documentation is provided:
- README.md in the rendering directory
- Detailed guide in docs/enhanced_rendering_guide.md
- Usage examples in docstrings and guides

## Usage Examples

**Render a conversation to HTML:**
```bash
poetry run carchive render conversation <conversation-id> --output-file output.html
```

**Render a collection to PDF:**
```bash
poetry run carchive render collection "Collection Name" output.pdf --format pdf
```

**Combine multiple collections:**
```bash
poetry run carchive render combined "Collection1" "Collection2" combined.html
```

**List available templates:**
```bash
poetry run carchive render templates
```

## Dependencies

- Markdown & PyMdown Extensions (core functionality)
- Jinja2 (templating)
- WeasyPrint (optional, for PDF generation)

## Future Enhancements

Potential future enhancements could include:
- More export formats (EPUB, DOCX)
- Interactive HTML components
- Theme customization options
- Automated table of contents generation