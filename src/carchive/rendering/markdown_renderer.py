# src/carchive/rendering/markdown_renderer.py
import re
import os
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
    
    def __init__(self, math_delimiters: Dict[str, List[str]] = None, web_mode: bool = False, api_url: str = None):
        """
        Initialize with optional custom math delimiters.
        
        Args:
            math_delimiters: Optional custom math delimiters
            web_mode: If True, use web-safe URLs instead of file:// URLs
            api_url: Base URL for API (used in web_mode)
        """
        # Default delimiters if none provided
        if math_delimiters is None:
            math_delimiters = {
                'inline': [['\\(', '\\)'], ['$', '$']],
                'display': [['\\[', '\\]'], ['$$', '$$']]
            }
            
        self.math_delimiters = math_delimiters
        
        # Web mode settings
        self.web_mode = web_mode
        self.api_url = api_url
    
    def render(self, text: str, message_id: str = None, extensions: List[str] = None) -> str:
        """
        Render markdown with enhanced LaTeX and image handling.
        
        Args:
            text: The markdown text to render
            message_id: Optional message ID to look up associated media
            extensions: Optional list of markdown extensions to use
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
                text = self.process_embedded_images(text, message_id)
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
                text = self.process_embedded_images(text, message_id)
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
    
    def process_embedded_images(self, text: str, message_id: str = None, session=None) -> str:
        """
        Process embedded images in markdown text.
        
        1. Handle local file references
        2. Handle data URLs
        3. Handle media references from the database
        4. Handle file-id references for uploaded and generated media
        5. Include associated media from the MessageMedia table
        
        Args:
            text: The markdown text to process
            message_id: Optional message ID to look up associated media
            session: Optional database session to use
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
                with get_session() as db_session:
                    # Check the columns available in the media table
                    media = db_session.query(Media).filter_by(id=media_id).first()
                    if media and hasattr(media, 'file_path') and media.file_path:
                        # Use API URL in web mode, file:// URL in CLI mode
                        if self.web_mode:
                            # Hardcoded URL for now to ensure it works
                            return f'![{alt_text}](http://localhost:8000/api/media/{media.id}/file)'
                        else:
                            return f'![{alt_text}](file://{os.path.abspath(media.file_path)})'
                    return f'![{alt_text}](missing-media-{media_id})'
            except Exception as e:
                # If there's a database error, just return the original reference with a note
                return f'![{alt_text}](media-reference-error-{media_id})'
        
        text = re.sub(media_pattern, media_replacement, text)
        
        # Process DALL-E asset references in the format [Asset: file-abc123]
        asset_pattern = r'\[Asset: (file-[a-zA-Z0-9]+)\]'
        
        def asset_replacement(match):
            file_id = match.group(1)
            
            try:
                with get_session() as db_session:
                    # Use ONLY exact match for original_file_id to avoid incorrect matching
                    media = db_session.query(Media).filter_by(original_file_id=file_id).first()
                    
                    if media and hasattr(media, 'file_path') and media.file_path:
                        if os.path.exists(media.file_path):
                            file_name = media.original_file_name or Path(media.file_path).name
                            # Use API URL in web mode, file:// URL in CLI mode
                            if self.web_mode:
                                # Hardcode for now to ensure it works
                                return f'![{file_name}](http://localhost:8000/api/media/{media.id}/file)'
                            else:
                                return f'![{file_name}](file://{os.path.abspath(media.file_path)})'
                        else:
                            return f'[Asset: {file_id} (file not found)]'
                    return f'[Asset: {file_id} (no media match)]'  # Keep original format with note
            except Exception as e:
                # If there's an error, just return the original text
                return f'[Asset: {file_id}]'
        
        text = re.sub(asset_pattern, asset_replacement, text)
        
        # Process standalone file-id references in the text (e.g., file-abc123)
        # These are references to uploaded files that need to be converted to proper image markdown
        # Use word boundaries to ensure we only match standalone file IDs, not ones within other text
        file_pattern = r'\b(file-[a-zA-Z0-9]+)\b'
        
        def file_id_replacement(match):
            file_id = match.group(1)
            
            try:
                with get_session() as db_session:
                    # Use ONLY exact match for original_file_id
                    media = db_session.query(Media).filter_by(original_file_id=file_id).first()
                    
                    if media and hasattr(media, 'file_path') and media.file_path:
                        if os.path.exists(media.file_path):
                            # Only convert to markdown if it's an image
                            if media.media_type == 'image':
                                file_name = media.original_file_name or Path(media.file_path).name
                                # Use API URL in web mode, file:// URL in CLI mode
                                if self.web_mode:
                                    # Hardcode for now to ensure it works
                                    return f'![{file_name}](http://localhost:8000/api/media/{media.id}/file)'
                                else:
                                    return f'![{file_name}](file://{os.path.abspath(media.file_path)})'
                            else:
                                # For non-images, use a link
                                file_name = media.original_file_name or Path(media.file_path).name
                                # Use API URL in web mode, file:// URL in CLI mode
                                if self.web_mode:
                                    # Hardcode for now to ensure it works
                                    return f'[{file_name}](http://localhost:8000/api/media/{media.id}/file)'
                                else:
                                    return f'[{file_name}](file://{os.path.abspath(media.file_path)})'
                        else:
                            # File doesn't exist on disk
                            return file_id
                    return file_id  # Keep as is if not found
            except Exception as e:
                # If there's an error, just return the original text
                return file_id
                
        text = re.sub(file_pattern, file_id_replacement, text)
        
        # If a message_id is provided, also include any associated media that isn't already referenced
        if message_id:
            try:
                with get_session() as db_session:
                    from carchive.database.models import MessageMedia
                    
                    # Find all media associated with this message
                    media_associations = db_session.query(MessageMedia, Media).join(
                        Media, MessageMedia.media_id == Media.id
                    ).filter(
                        MessageMedia.message_id == message_id
                    ).all()
                    
                    # For each associated media, check if it's already referenced in the text
                    for assoc, media in media_associations:
                        # Skip if the media's original_file_id is already in the text
                        if media.original_file_id:
                            # Check if it appears in an [Asset: file-ID] pattern
                            if f'[Asset: {media.original_file_id}]' in text:
                                continue
                            # Check for standalone file-ID
                            if media.original_file_id in text:
                                continue
                            
                        # Skip if the media's ID is already in the text (as a media: reference)
                        if f'media:{media.id}' in text:
                            continue
                            
                        # Skip if the file path is already referenced
                        if media.file_path and os.path.abspath(media.file_path) in text:
                            continue
                            
                        # If not already referenced, append the media reference at the end
                        if media.file_path and os.path.exists(media.file_path):
                            if media.media_type == 'image':
                                file_name = media.original_file_name or Path(media.file_path).name
                                # Use API URL in web mode, file:// URL in CLI mode
                                if self.web_mode:
                                    # Hardcode for now to ensure it works
                                    text = text + f'\n\n![{file_name}](http://localhost:8000/api/media/{media.id}/file)'
                                else:
                                    text = text + f'\n\n![{file_name}](file://{os.path.abspath(media.file_path)})'
                            else:
                                file_name = media.original_file_name or Path(media.file_path).name
                                # Use API URL in web mode, file:// URL in CLI mode
                                if self.web_mode:
                                    # Hardcode for now to ensure it works
                                    text = text + f'\n\n[{file_name}](http://localhost:8000/api/media/{media.id}/file)'
                                else:
                                    text = text + f'\n\n[{file_name}](file://{os.path.abspath(media.file_path)})'
            except Exception as e:
                # If there's an error, just continue without adding associated media
                print(f"Error processing associated media for message {message_id}: {str(e)}")
        
        return text