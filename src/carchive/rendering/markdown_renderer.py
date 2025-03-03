# src/carchive/rendering/markdown_renderer.py
import re
import markdown
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from markdown.extensions.codehilite import CodeHiliteExtension
from pymdownx.arithmatex import ArithmatexExtension
from carchive.database.session import get_session
from carchive.database.models import Media

class MarkdownRenderer:
    """
    Enhanced markdown renderer with LaTeX repair and image handling.
    """
    
    def __init__(self, math_delimiters: Dict[str, List[str]] = None):
        """
        Initialize with optional custom math delimiters.
        """
        self.math_delimiters = math_delimiters or {
            'inline': [['\\(', '\\)'], ['$', '$']],
            'display': [['\\[', '\\]'], ['$$', '$$']]
        }
    
    def render(self, text: str, extensions: List[str] = None) -> str:
        """
        Render markdown with enhanced LaTeX and image handling.
        """
        if text is None or not isinstance(text, str):
            return ""
        
        # Handle display math blocks with [..] delimiter style
        # This pattern matches blocks that start with [ on a line by itself and end with ] on a line by itself
        text = re.sub(r'^\s*\[\s*$\n(.*?)\n\s*\]\s*$', 
                      r'$$\n\1\n$$', 
                      text, 
                      flags=re.MULTILINE | re.DOTALL)
        
        # Also handle inline display blocks that appear within regular text
        # This handles cases with square brackets that have LaTeX inside
        text = re.sub(r'\[\n(.*?)\n\]', 
                     r'$$\n\1\n$$', 
                     text, 
                     flags=re.DOTALL)
        
        # Skip LaTeX/math repair for non-math content
        if '\\' not in text and '$' not in text and '[' not in text:
            # Simpler and faster path for non-math content
            # Only process embedded images if database is available
            try:
                text = self.process_embedded_images(text)
            except Exception as e:
                # If there's a database or model error, just continue without processing images
                print(f"Warning: Unable to process embedded images: {str(e)}")
            
            # Default extensions without ArithmatexExtension
            if extensions is None:
                extensions = ["extra", CodeHiliteExtension(), "fenced_code", "nl2br"]
                
            # Render with markdown
            return markdown.markdown(
                text,
                extensions=extensions
            )
        
        # For math content, apply the full processing pipeline
        # Preprocess text
        original_text = text
        try:
            text = self.repair_latex_delimiters(text)
            
            # Only process embedded images if database is available
            try:
                text = self.process_embedded_images(text)
            except Exception as e:
                # If there's a database or model error, just continue without processing images
                print(f"Warning: Unable to process embedded images: {str(e)}")
            
            # Default extensions
            if extensions is None:
                # Configure the Arithmatex extension more carefully
                arithmatex_ext = ArithmatexExtension(
                    generic=True,
                    preview=False,
                    smart_dollar=False  # Disable smart_dollar to prevent issues
                )
                extensions = ["extra", CodeHiliteExtension(), arithmatex_ext, "fenced_code", "nl2br"]
                
            # Render with markdown
            html = markdown.markdown(
                text,
                extensions=extensions
            )
            
            # Post-process to handle display math that wasn't properly processed
            # Pattern 1: Look for bare math blocks and wrap them in proper display math tags
            html = re.sub(r'<p>\s*\$\$\s*<br />\n(.*?)\n\s*\$\$\s*</p>', 
                          r'<div class="arithmatex">\[ \1 \]</div>', 
                          html, 
                          flags=re.DOTALL)
                          
            # Pattern 2: Handle square bracket notation directly in HTML output 
            # This is a fallback for cases that weren't caught earlier
            html = re.sub(r'<p>\s*\[\s*<br />\n(.*?)\n\s*\]\s*</p>', 
                          r'<div class="arithmatex">\[ \1 \]</div>', 
                          html, 
                          flags=re.DOTALL)
                          
            # Pattern 3: Handle cases where brackets are on same line as content
            # Only if they appear to be mathematical content (has LaTeX commands)
            # and not reference numbers like [1], [2], etc.
            html = re.sub(r'<p>\s*\[([^0-9\]]*?\\[a-zA-Z{}_\^][^0-9\]]*?)\]\s*</p>', 
                          r'<div class="arithmatex">\[ \1 \]</div>', 
                          html)
                          
            # Pattern 4: Convert any raw LaTeX block that wasn't processed
            html = re.sub(r'<p>(\\\[.*?\\\])</p>', 
                          r'<div class="arithmatex">\1</div>', 
                          html, 
                          flags=re.DOTALL)
            
            return html
        except Exception as e:
            # Fallback to basic rendering if math processing fails
            print(f"Warning: Math processing failed, using basic rendering: {str(e)}")
            if extensions is None:
                extensions = ["extra", CodeHiliteExtension(), "fenced_code", "nl2br"]
            
            return markdown.markdown(
                original_text, 
                extensions=extensions
            )
    
    def repair_latex_delimiters(self, text: str) -> str:
        """
        Repair common LaTeX delimiter corruption issues.
        Much more carefully than before - only look for clear math patterns.
        """
        if not text:
            return text
            
        # Fix equation/align environments properly for MathJax
        text = re.sub(r'\\begin{align}(.*?)\\end{align}', r'\\[\1\\]', text, flags=re.DOTALL)
        text = re.sub(r'\\begin{equation}(.*?)\\end{equation}', r'\\[\1\\]', text, flags=re.DOTALL)
        text = re.sub(r'\\begin{aligned}(.*?)\\end{aligned}', r'\\[\1\\]', text, flags=re.DOTALL)
        text = re.sub(r'\\begin{gather}(.*?)\\end{gather}', r'\\[\1\\]', text, flags=re.DOTALL)
        text = re.sub(r'\\begin{multline}(.*?)\\end{multline}', r'\\[\1\\]', text, flags=re.DOTALL)
        
        # Double dollar signs to display math - but only with clear start/end
        text = re.sub(r'(?<!\$)(\$\$)([^\$]+?)(\$\$)(?!\$)', r'\\[\2\\]', text)
        
        # Single dollar signs to inline math - be very careful here, must have clear mathematical content
        text = re.sub(r'(?<!\$)\$(\\?[a-zA-Z0-9_\\{}()\[\]^+-=*/]+)\$(?!\$)', r'\\(\1\\)', text)
        
        # Clean up any nested delimiters - important to prevent \( \) inside equations
        # This removes any inline delimiters that are inside display math
        text = re.sub(r'(\\\[.*?)\\[\(\[](.+?)\\[\)\]](.+?\\\])', r'\1\2\3', text, flags=re.DOTALL)
        text = re.sub(r'(\$\$.*?)\\[\(\[](.+?)\\[\)\]](.+?\$\$)', r'\1\2\3', text, flags=re.DOTALL)
        
        # Handle explicit LaTeX constructs when not in math mode
        math_patterns = [
            # Fractions
            r'\\frac{[^}]+}{[^}]+}',
            # Subscripts/superscripts
            r'\\?[a-zA-Z]_\{[^}]+\}',
            r'\\?[a-zA-Z]\^\{[^}]+\}',
            # Common mathematical functions
            r'\\(sin|cos|tan|log|ln|exp|lim|sum|prod|int)\{[^}]*\}',
            # Math operators
            r'\\(times|div|cdot|pm|mp|leq|geq|neq|approx|equiv|cong|sim)'
        ]
        
        # Ensure these patterns are wrapped in math delimiters if not already
        for pattern in math_patterns:
            # Only match if not already in math mode
            text = re.sub(f'(?<!\\\\[\\[(])({pattern})(?![^\\(]*\\\\[\\])])', r'\\(\1\\)', text)
        
        # Fix missing closing delimiters only if needed
        open_inline = text.count('\\(')
        close_inline = text.count('\\)')
        open_display = text.count('\\[')
        close_display = text.count('\\]')
        
        # Add missing closing delimiters when truly needed
        if open_inline > close_inline:
            missing_close = open_inline - close_inline
            text = text + '\\)' * missing_close
            
        if open_display > close_display:
            missing_close = open_display - close_display
            text = text + '\\]' * missing_close
            
        return text
    
    def process_embedded_images(self, text: str) -> str:
        """
        Process embedded images in markdown text.
        
        1. Handle local file references
        2. Handle data URLs
        3. Handle media references from the database
        """
        if not text:
            return text
            
        # Pattern for local image references
        # ![alt text](file:path/to/image.jpg) -> ![alt text](/media/images/image.jpg)
        img_pattern = r'!\[(.*?)\]\(file:(.*?)\)'
        text = re.sub(img_pattern, r'![Image: \1](/media/images/\2)', text)
        
        # Detect media references
        # ![alt text](media:uuid) -> ![alt text](/media/uuid/filename)
        media_pattern = r'!\[(.*?)\]\(media:([a-f0-9-]+)\)'
        
        def media_replacement(match):
            media_id = match.group(2)
            alt_text = match.group(1)
            
            # Look up media path in database
            try:
                with get_session() as session:
                    # Check the columns available in the media table
                    media = session.query(Media).filter_by(id=media_id).first()
                    if media and hasattr(media, 'file_path') and media.file_path:
                        return f'![{alt_text}](/media/{media_id}/{Path(media.file_path).name})'
                    return f'![{alt_text}](missing-media-{media_id})'
            except Exception as e:
                # If there's a database error, just return the original reference with a note
                return f'![{alt_text}](media-reference-error-{media_id})'
        
        text = re.sub(media_pattern, media_replacement, text)
        
        return text