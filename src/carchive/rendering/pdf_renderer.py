# src/carchive/rendering/pdf_renderer.py
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import importlib.util

from carchive.rendering.base_renderer import ContentRenderer
from carchive.rendering.html_renderer import HTMLRenderer

# Check if WeasyPrint is available
WEASYPRINT_AVAILABLE = importlib.util.find_spec("weasyprint") is not None

class PDFRenderer(ContentRenderer):
    """
    PDF renderer implementation for rendering content to PDF format.
    
    This renderer requires WeasyPrint to be properly installed.
    If WeasyPrint is not available, the renderer will raise an exception
    when trying to generate a PDF.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize with optional templates directory.
        """
        self.html_renderer = HTMLRenderer(templates_dir)
        
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            print("WARNING: WeasyPrint is not available. PDF generation will not work.")
            print("Please install WeasyPrint and its dependencies:")
            print("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
    
    def render_text(self, text: str) -> bytes:
        """
        Render text content to PDF.
        """
        html_content = self.html_renderer.render_text(text)
        return self._html_to_pdf(html_content)
    
    def render_collection(self, collection_name: str, output_path: str, 
                         template: str = "default", include_metadata: bool = False) -> str:
        """
        Render a collection to PDF.
        """
        # First render to HTML
        html_content = self.html_renderer.render_collection(
            collection_name=collection_name, 
            output_path=None,  # Don't write HTML to file
            template=template,
            include_metadata=include_metadata
        )
        
        # Then convert HTML to PDF
        pdf_data = self._html_to_pdf(html_content)
        
        # Write to file if output_path provided
        if output_path:
            Path(output_path).write_bytes(pdf_data)
            
        return output_path
    
    def render_conversation(self, conversation_id: str, output_path: str,
                            template: str = "default", include_raw: bool = False) -> str:
        """
        Render a conversation to PDF.
        """
        # First render to HTML
        html_content = self.html_renderer.render_conversation(
            conversation_id=conversation_id,
            output_path=None,  # Don't write HTML to file
            template=template,
            include_raw=include_raw
        )
        
        # Then convert HTML to PDF
        pdf_data = self._html_to_pdf(html_content)
        
        # Write to file if output_path provided
        if output_path:
            Path(output_path).write_bytes(pdf_data)
            
        return output_path
    
    def render_search_results(self, results: List[Dict[str, Any]], output_path: str,
                             template: str = "default") -> str:
        """
        Render search results to PDF.
        """
        # First render to HTML
        html_content = self.html_renderer.render_search_results(
            results=results,
            output_path=None,  # Don't write HTML to file
            template=template
        )
        
        # Then convert HTML to PDF
        pdf_data = self._html_to_pdf(html_content)
        
        # Write to file if output_path provided
        if output_path:
            Path(output_path).write_bytes(pdf_data)
            
        return output_path
    
    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML content to PDF.
        
        Raises:
            ImportError: If WeasyPrint is not available
        """
        # Check if WeasyPrint is available
        if not WEASYPRINT_AVAILABLE:
            raise ImportError(
                "WeasyPrint is not available. Please install WeasyPrint and its dependencies:\n"
                "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation"
            )
        
        # Import WeasyPrint only when needed
        import weasyprint
        
        # Define PDF-specific CSS
        pdf_css = weasyprint.CSS(string="""
            @page {
                margin: 1cm;
                @bottom-center {
                    content: "Page " counter(page) " of " counter(pages);
                }
            }
            body { font-family: sans-serif; }
            pre { white-space: pre-wrap; }
            img { max-width: 100%; height: auto; }
        """)
        
        # Generate PDF
        pdf = weasyprint.HTML(string=html_content).write_pdf(stylesheets=[pdf_css])
        return pdf