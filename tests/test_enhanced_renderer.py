# tests/test_enhanced_renderer.py
import pytest
from pathlib import Path
import os
import re
import tempfile
import importlib.util

from carchive.rendering.markdown_renderer import MarkdownRenderer
from carchive.rendering.html_renderer import HTMLRenderer

# Check if WeasyPrint is available
WEASYPRINT_AVAILABLE = importlib.util.find_spec("weasyprint") is not None

# Sample content with different markdown elements and potential issues
# Use r-string to avoid escaping issues
SAMPLE_CONTENT = r"""
# This is a test markdown document

This is a paragraph with **bold** and *italic* text.

## LaTeX Examples

Inline math: $E = mc^2$ and \(F = ma\) should both render properly.

Display math: 
$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$

And another with different delimiters:
\[\int_{a}^{b} f(x) dx = F(b) - F(a)\]

## Code Examples

```python
def test_function():
    return "Hello World"
```

## Table Examples

| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |

## Corrupted LaTeX Examples

This equation is missing a closing delimiter: $E = mc^2

This one has double dollars in weird places: $$ x^2 + y^2 = r^2 $$

## Potential Issues

Escaped characters: \* \_ \\ should appear as literal characters.

HTML tags: <div>Test</div> should be escaped or rendered properly.
"""

# Create a simplified version of MarkdownRenderer for testing that doesn't use the database
class TestMarkdownRenderer(MarkdownRenderer):
    def process_embedded_images(self, text: str) -> str:
        """Override to avoid database calls"""
        if not text:
            return text
            
        # Pattern for local image references
        img_pattern = r'!\[(.*?)\]\(file:(.*?)\)'
        text = re.sub(img_pattern, r'![Image: \1](/media/images/\2)', text)
        
        # Just convert media references to a standard format without DB lookup
        media_pattern = r'!\[(.*?)\]\(media:([a-f0-9-]+)\)'
        text = re.sub(media_pattern, r'![\1](/media/\2/file.jpg)', text)
        
        return text

def test_markdown_renderer():
    """Test the enhanced markdown renderer without database access"""
    # Use the test renderer that doesn't need the database
    renderer = TestMarkdownRenderer()
    result = renderer.render(SAMPLE_CONTENT)
    
    # Check that LaTeX content was properly rendered
    assert 'class="arithmatex"' in result  # LaTeX should be formatted for MathJax
    assert 'type="math/tex"' in result  # LaTeX should use MathJax 
    
    # Check that basic content was rendered properly
    assert "<h1>" in result
    assert "<strong>bold</strong>" in result
    assert "<em>italic</em>" in result
    assert "<table>" in result
    
    # Print the result for manual inspection if verbose
    if os.environ.get("VERBOSE", "0") == "1":
        print("\n=== MARKDOWN RENDERER OUTPUT ===")
        print(result)
        print("===============================\n")

def test_html_renderer():
    """Test the HTML renderer with the test markdown renderer"""
    # Create an HTMLRenderer that uses our test markdown renderer
    html_renderer = HTMLRenderer()
    html_renderer.markdown_renderer = TestMarkdownRenderer()
    
    # Create a temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as temp:
        temp_path = temp.name
    
    try:
        # Test direct text rendering
        html_content = html_renderer.render_text(SAMPLE_CONTENT)
        assert "<h1>" in html_content
        assert "LaTeX Examples" in html_content
        
        # Write to a file for inspection
        Path(temp_path).write_text(
            f"""<!DOCTYPE html>
            <html>
            <head>
                <title>Test Markdown</title>
                <script>
                MathJax = {{
                  tex: {{
                    inlineMath: [["\\\\(","\\\\)"], ["$","$"]],
                    displayMath: [["\\\\[","\\\\]"], ["$$","$$"]]
                  }}
                }};
                </script>
                <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
            </head>
            <body>
                {html_content}
            </body>
            </html>""",
            encoding="utf-8"
        )
        
        # Print the file location if verbose
        if os.environ.get("VERBOSE", "0") == "1":
            print(f"\nHTML output written to: {temp_path}")
    finally:
        # Clean up temp file unless we want to keep it for inspection
        if os.environ.get("KEEP_FILES", "0") != "1":
            try:
                os.unlink(temp_path)
            except:
                pass

@pytest.mark.skipif(not WEASYPRINT_AVAILABLE,
                    reason="WeasyPrint not available")
def test_pdf_renderer():
    """Test the PDF renderer if WeasyPrint is installed"""
    try:
        from carchive.rendering.pdf_renderer import PDFRenderer
        
        # Create a PDFRenderer that uses our test markdown renderer
        pdf_renderer = PDFRenderer()
        pdf_renderer.html_renderer.markdown_renderer = TestMarkdownRenderer()
        
        # Create a temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
            temp_path = temp.name
        
        try:
            # Test direct text rendering
            pdf_data = pdf_renderer.render_text(SAMPLE_CONTENT)
            assert isinstance(pdf_data, bytes)
            assert len(pdf_data) > 0
            
            # Write to a file for inspection
            Path(temp_path).write_bytes(pdf_data)
            
            # Print the file location if verbose
            if os.environ.get("VERBOSE", "0") == "1":
                print(f"\nPDF output written to: {temp_path}")
        finally:
            # Clean up temp file unless we want to keep it for inspection
            if os.environ.get("KEEP_FILES", "0") != "1":
                try:
                    os.unlink(temp_path)
                except:
                    pass
    except ImportError:
        pytest.skip("WeasyPrint not installed correctly, skipping PDF tests")

if __name__ == "__main__":
    # Run tests directly
    test_markdown_renderer()
    test_html_renderer()
    
    # Only run PDF test if WeasyPrint is available
    if WEASYPRINT_AVAILABLE:
        test_pdf_renderer()