# Enhanced Rendering System Guide

This guide covers the enhanced rendering system for Carchive, which provides robust handling of Markdown content, LaTeX equations, embedded images, DALL-E AI-generated images, gencom fields, and support for multiple output formats including HTML and PDF.

## Overview

The enhanced rendering system includes:

1. **Unified Rendering Architecture**
   - Base class interface
   - Specialized renderer implementations
   - Template-based output generation

2. **Enhanced Markdown Handling**
   - LaTeX repair for common corruption patterns
   - Image reference handling
   - Media database integration
   - DALL-E AI-generated image support
   - Parent-child message relationship tracking

3. **Multiple Output Formats**
   - HTML output with customizable templates
   - PDF generation via WeasyPrint
   
4. **Gencom Fields Support**
   - Display agent thought process and analysis
   - Configurable field selection
   - Custom field label mapping
   
5. **Media Display Options**
   - Inline image display
   - Gallery layout for multiple images
   - Thumbnail view with captions

## Installation Requirements

The enhanced rendering system requires the following packages:

```bash
# Core dependencies
pip install markdown pymdown-extensions

# PDF support
pip install weasyprint

# Template support
pip install jinja2
```

These are already included in the project's dependencies.

## Command Line Usage

### Rendering Conversations

```bash
# Basic rendering to HTML
poetry run carchive render conversation <conversation-id> --output-file output.html

# Render to PDF
poetry run carchive render conversation <conversation-id> --output-file output.pdf --format pdf

# Include raw markdown in the output (for debugging)
poetry run carchive render conversation <conversation-id> --include-raw

# DALL-E and media rendering options
poetry run carchive render conversation <conversation-id> --media-display=gallery

# Gencom fields rendering
poetry run carchive render conversation <conversation-id> --gencom-fields=all
poetry run carchive render conversation <conversation-id> --gencom-fields=thinking_process,relevant_info

# Custom labels for gencom fields
poetry run carchive render conversation <conversation-id> --gencom-fields=thinking_process,relevant_info \
  --gencom-field-labels="thinking_process:Reasoning,relevant_info:Context"

# Complete example with all options
poetry run carchive render conversation <conversation-id> output.html \
  --media-display=gallery \
  --gencom-fields=thinking_process,relevant_info \
  --gencom-field-labels="thinking_process:Reasoning,relevant_info:Context" \
  --template=academic
```

### Rendering Individual Messages

```bash
# Render a message to HTML
poetry run carchive render message <message-id> output.html

# Render a message to PDF
poetry run carchive render message <message-id> output.pdf --format pdf

# Include metadata in the output
poetry run carchive render message <message-id> output.html --include-metadata

# Use a specific template
poetry run carchive render message <message-id> output.html --template academic
```

### Rendering Chunks

```bash
# Render a chunk to HTML
poetry run carchive render chunk <chunk-id> output.html

# Render a chunk to PDF
poetry run carchive render chunk <chunk-id> output.pdf --format pdf

# Include metadata in the output
poetry run carchive render chunk <chunk-id> output.html --include-metadata
```

### Rendering Buffers

```bash
# Render a buffer's contents to HTML
poetry run carchive render buffer <buffer-name> output.html

# Render a buffer's contents to PDF
poetry run carchive render buffer <buffer-name> output.pdf --format pdf

# Include metadata in the output
poetry run carchive render buffer <buffer-name> output.html --include-metadata
```

### Rendering Collections

```bash
# Render a collection to HTML
poetry run carchive render collection "Collection Name" output.html

# Render a collection to PDF with metadata
poetry run carchive render collection "Collection Name" output.pdf --format pdf --include-metadata

# Use a specific template
poetry run carchive render collection "Collection Name" output.html --template academic
```

### Combining Multiple Collections

```bash
# Render multiple collections to a single HTML file
poetry run carchive render combined "Collection1" "Collection2" combined.html

# Render multiple collections to PDF with a custom title
poetry run carchive render combined "Collection1" "Collection2" combined.pdf --format pdf --title "Research Summary"
```

### Listing Available Templates and Formats

```bash
# Show available rendering templates
poetry run carchive render templates

# Show available output formats
poetry run carchive render formats
```

## Programmatic Usage

### Rendering Markdown

```python
from carchive.rendering import MarkdownRenderer

# Create a renderer
renderer = MarkdownRenderer()

# Render markdown text
html_content = renderer.render("""
# Example Markdown

This is some example text with a LaTeX equation: $E = mc^2$

And an image: ![Image](media:12345678-1234-5678-1234-567812345678)
""")

print(html_content)
```

### Rendering to HTML

```python
from carchive.rendering import HTMLRenderer

# Create an HTML renderer
renderer = HTMLRenderer()

# Render a collection
html_content = renderer.render_collection(
    collection_name="Research Notes",
    output_path="research.html",
    template="academic",
    include_metadata=True
)

# Render a conversation
html_content = renderer.render_conversation(
    conversation_id="conv-uuid-here",
    output_path="conversation.html",
    template="default",
    include_raw=False
)
```

### Rendering to PDF

```python
from carchive.rendering import PDFRenderer

# Create a PDF renderer
renderer = PDFRenderer()

# Render a collection to PDF
renderer.render_collection(
    collection_name="Research Notes",
    output_path="research.pdf",
    template="academic",
    include_metadata=False
)
```

## Templates

The rendering system includes the following templates:

1. **default.html** - Clean, simple layout with role-based styling
2. **academic.html** - Academic paper-style formatting with serif fonts

### Creating Custom Templates

Create custom templates in the `src/carchive/rendering/templates/` directory with a `.html` extension. Templates use Jinja2 syntax and receive the following context variables:

- `title` - The title of the rendered content
- `subtitle` - Optional subtitle
- `items` - List of content items with:
  - `role` - Message role (user, assistant, tool, unknown)
  - `content` - Rendered HTML content
  - `metadata` - Optional metadata dictionary
  - `header` - Optional header text
- `include_metadata` - Boolean flag for including metadata
- `show_color_key` - Boolean flag for showing the color key

## LaTeX Handling

The enhanced system repairs common LaTeX rendering issues:

1. **Missing Delimiters**: Adds missing closing delimiters
2. **Delimiter Conversion**: Standardizes delimiters to `\( \)` and `\[ \]`
3. **Environment Conversion**: Converts environments like `\begin{equation}` to `\[ \]`
4. **Square Bracket Notation**: Converts `[...]` display math notation to proper delimiters
5. **Nested Delimiter Cleanup**: Removes nested delimiters like `\(` and `\)` inside equations
6. **Client-side Processing**: Uses JavaScript to handle edge cases and ensure proper rendering

### LaTeX Rendering Implementation Details

The LaTeX rendering system operates in two phases:

#### Server-side Processing (Python)

1. **Preprocessing**: 
   - Converts square bracket math blocks to dollar sign notation
   - Converts LaTeX environments to proper display math
   - Repairs inline math delimiters

2. **Markdown Processing**:
   - Uses the Arithmatex extension with careful configuration
   - Sets `smart_dollar=False` to prevent issues with dollar signs

3. **Post-processing**:
   - Wraps unprocessed math blocks in proper HTML
   - Handles edge cases like square brackets in HTML

#### Client-side Processing (JavaScript)

1. **Element Processing**:
   - Scans for unprocessed math blocks in HTML
   - Converts them to proper MathJax format

2. **Cleanup**:
   - Removes excess backslashes
   - Eliminates nested delimiters that cause red text
   - Ensures proper math delimiters

3. **Typesetting**:
   - Forces MathJax to typeset all math content
   - Provides backup typesetting on page load

### Known Edge Cases

Some LaTeX notation still needs improvement:

1. **Equations in paragraphs**: Text with inline math like `\partial_\mu J^\mu = 0` without proper delimiters
2. **Cross-element LaTeX**: When LaTeX expressions span multiple HTML elements
3. **LaTeX text commands**: Special handling for `\text{}`, `\quad`, etc.
4. **Reference numbers**: Preventing `[1]`, `[2]` from being treated as math

The recommended solution is preserved in `docs/working_latex_renderer_backup.py`.

## Image Handling

The system handles different types of image references:

1. **Local File References**: `![Alt text](file:path/to/image.jpg)`
2. **Media Database References**: `![Alt text](media:uuid-here)`
3. **Regular URLs**: `![Alt text](https://example.com/image.jpg)`
4. **File ID References**: `file-abc123` (used in ChatGPT exports)
5. **DALL-E Generated Images**: AI-generated images from DALL-E with "AI Generated" badge

### Media Display Modes

You can choose how media is displayed using the `--media-display` option:

- `inline`: Shows images in full size directly in the conversation flow (default)
- `gallery`: Displays images in a grid layout when multiple images are present
- `thumbnails`: Shows smaller thumbnail versions that can be clicked to view full size

### DALL-E Image Detection

The system automatically detects DALL-E generated images through:

1. The `is_generated` flag in the Media table
2. Parent-child message relationships (tool messages with DALL-E prompts)
3. Message content analysis for DALL-E references
4. File naming patterns in the original archive

### Parent-Child Rendering

For complex message relationships, the renderer now:

1. Follows parent-child links between messages
2. Associates tool messages containing DALL-E prompts with assistant messages
3. Displays generated images with proper attribution
4. Shows images in the correct message context

## Troubleshooting

### Rendering Wrapper Script

To suppress verbose logging from numexpr and other libraries, a wrapper script is provided:

```bash
# Use the wrapper script to render without logging noise
./run_render.sh conversation YOUR_CONVERSATION_ID --output-file output.html

# The script accepts all the same arguments as the normal render command
./run_render.sh message YOUR_MESSAGE_ID --output-file output.html --template academic
```

The script simply redirects stderr to /dev/null to prevent distracting logging messages.

### PDF Generation Issues

If PDF generation fails:

1. Ensure WeasyPrint is properly installed
2. Check for unsupported HTML/CSS features
3. Look for malformed LaTeX that might cause rendering issues

### Template Issues

If templates aren't loading:

1. Ensure template files are in the correct directory
2. Check that template names are specified correctly (without the .html extension)
3. Verify Jinja2 is installed

### LaTeX Rendering Problems

For LaTeX that doesn't render properly:

1. Check the HTML source for correct MathJax delimiters
2. Ensure MathJax is loading properly (check console for errors)
3. Try using different delimiter styles in your markdown source

## Gencom Fields Integration

Gencom fields allow displaying the agent's thought process alongside normal message content.

### Displaying Gencom Fields

Control which gencom fields are displayed using the `--gencom-fields` option:

- `none`: Don't display any gencom fields (default)
- `all`: Display all available gencom fields
- Field list: Specify comma-separated field names (e.g., `thinking_process,relevant_info`)

### Custom Field Labels

You can customize how field names are displayed with the `--gencom-field-labels` option, using a comma-separated list of `field:Label` pairs:

```bash
--gencom-field-labels="thinking_process:Reasoning,relevant_info:Context"
```

### Adding Your Own Gencom Fields

To add gencom fields to messages, update the message's `meta_info` JSON to include a `gencom` object:

```json
{
  "meta_info": {
    "gencom": {
      "thinking_process": "Here's my step-by-step reasoning...",
      "relevant_info": "The key information I considered was..."
    }
  }
}
```

These fields will then be displayed when using the appropriate render options.