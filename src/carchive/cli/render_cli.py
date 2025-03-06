# src/carchive/cli/render_cli.py
import typer
from pathlib import Path
from typing import List, Optional
import importlib.util
import uuid
import logging
import sys
import os

# Configure the logging system to suppress all logs except errors
logging.basicConfig(level=logging.ERROR)

# Create a specific filter to remove "NumExpr defaulting" messages
class NumExprFilter(logging.Filter):
    def filter(self, record):
        return "NumExpr defaulting" not in record.getMessage()

# Apply this filter to all handlers
for handler in logging.root.handlers:
    handler.addFilter(NumExprFilter())

# Explicitly configure the specific loggers we want to silence
for logger_name in ['numexpr', 'numexpr.utils', 'MARKDOWN']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)
    # Also add our filter to this logger's handlers
    for handler in logger.handlers:
        handler.addFilter(NumExprFilter())

# Redirect stdout temporarily to capture imports that might print directly
import os
import sys
old_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

# Import numexpr to trigger any first-time setup messages
try:
    import numexpr
except:
    pass

# Restore stdout
sys.stdout.close()
sys.stdout = old_stdout

# Check if WeasyPrint is available
WEASYPRINT_AVAILABLE = importlib.util.find_spec("weasyprint") is not None

# Import legacy renderer for backward compatibility
from carchive.rendering.conversation_renderer import render_conversation_html

# Import enhanced renderers
from carchive.rendering.html_renderer import HTMLRenderer
from carchive.database.session import get_session
from carchive.database.models import Collection, Message, Chunk, Conversation, ResultsBuffer as Buffer, BufferItem, Media, MessageMedia

# Conditionally import PDF renderer
if WEASYPRINT_AVAILABLE:
    from carchive.rendering.pdf_renderer import PDFRenderer
else:
    PDFRenderer = None

render_app = typer.Typer(help="Render content to various formats.")

# Available output formats
OUTPUT_FORMATS = ["html", "pdf"] if WEASYPRINT_AVAILABLE else ["html"]

@render_app.command("conversation")
def conversation_cmd(
    conversation_id: str, 
    output_file: str = "conversation.html",
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_raw: bool = typer.Option(False, help="Include raw markdown in output"),
    media_display: str = typer.Option("inline", help="Media display mode: inline, gallery, or thumbnails"),
    gencom_fields: str = typer.Option("none", help="Gencom fields to display: none, all, or comma-separated list"),
    gencom_field_labels: str = typer.Option("", help="Field name mapping (e.g. 'thinking_process:Reasoning,relevant_info:Context')")
):
    """
    Render a conversation to a file in the specified format.
    
    This command renders a full conversation, including messages and optionally media and gencom fields.
    
    Examples:
        carchive render conversation 12345 output.html
        carchive render conversation 12345 output.html --gencom-fields=all
        carchive render conversation 12345 output.html --gencom-fields=thinking_process,relevant_info
        carchive render conversation 12345 output.html --media-display=gallery
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Validate media display mode
    valid_display_modes = ["inline", "gallery", "thumbnails"]
    if media_display not in valid_display_modes:
        typer.echo(f"Error: Invalid media display mode '{media_display}'. Valid modes: {', '.join(valid_display_modes)}")
        raise typer.Exit(1)
        
    # Process gencom field labels if provided
    field_labels_dict = {}
    if gencom_field_labels:
        try:
            for mapping in gencom_field_labels.split(','):
                field, label = mapping.split(':', 1)
                field_labels_dict[field.strip()] = label.strip()
        except ValueError:
            typer.echo("Error: Invalid format for gencom field labels. Use 'field:Label,another:Another Label'")
            raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Render conversation
    try:
        renderer.render_conversation(
            conversation_id=conversation_id,
            output_path=str(output_path),
            template=template,
            include_raw=include_raw,
            gencom_fields=gencom_fields,
            gencom_field_labels=field_labels_dict,
            media_display_mode=media_display
        )
        typer.echo(f"Conversation {conversation_id} rendered to {output_path}")
    except Exception as e:
        typer.echo(f"Error rendering conversation: {str(e)}")
        raise typer.Exit(1)

@render_app.command("collection")
def collection_cmd(
    collection_name: str,
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(False, help="Include metadata in the output")
):
    """
    Render a collection to a file in the specified format.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Render collection
    try:
        renderer.render_collection(
            collection_name=collection_name,
            output_path=str(output_path),
            template=template,
            include_metadata=include_metadata
        )
        typer.echo(f"Collection '{collection_name}' rendered to {output_path}")
    except Exception as e:
        typer.echo(f"Error rendering collection: {str(e)}")
        raise typer.Exit(1)

@render_app.command("combined")
def combined_cmd(
    collections: List[str] = typer.Argument(..., help="Names of collections to render"),
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    title: Optional[str] = typer.Option(None, help="Custom title for the combined output")
):
    """
    Render multiple collections into a single file.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Verify collections exist
    with get_session() as session:
        for coll_name in collections:
            if not session.query(Collection).filter_by(name=coll_name).first():
                typer.echo(f"Error: Collection '{coll_name}' not found.")
                raise typer.Exit(1)
    
    # Generate title if not provided
    if not title:
        title = f"Combined Collections: {', '.join(collections)}"
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Render each collection and combine
    try:
        combined_content = []
        
        for collection_name in collections:
            # For HTML, we'll render each collection separately and combine
            collection_content = renderer.render_collection(
                collection_name=collection_name,
                output_path=None,  # Don't write to file yet
                template=template,
                include_metadata=False
            )
            
            if format == "html":
                # Extract just the content part for HTML
                # This is a simplistic approach - a more robust approach would parse the HTML
                start_marker = "<div class=\"content\">"
                end_marker = "</div>\n  \n  <div class=\"color-key\">"
                start_idx = collection_content.find(start_marker)
                end_idx = collection_content.find(end_marker)
                
                if start_idx >= 0 and end_idx >= 0:
                    content_part = collection_content[start_idx + len(start_marker):end_idx]
                    combined_content.append(content_part)
        
        # Create combined output
        if format == "html":
            html_renderer = HTMLRenderer()
            context = {
                "title": title,
                "items": [],  # We'll insert combined_content directly in the template
                "include_metadata": False,
                "show_color_key": True,
                "custom_content": "".join(combined_content)
            }
            
            # Create a template engine and get the template
            from carchive.rendering.template_engine import TemplateEngine
            template_engine = TemplateEngine()
            
            # Custom template that supports combined content
            html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 1em auto; max-width: 800px; line-height: 1.5; }}
    .role-user {{ background: #e0f7fa; margin: .75em 0; padding: .5em; border-radius: 5px; }}
    .role-assistant {{ background: #f1f8e9; margin: .75em 0; padding: .5em; border-radius: 5px; }}
    .role-tool {{ background: #fff3e0; margin: .75em 0; padding: .5em; border-radius: 5px; }}
    .role-unknown {{ background: #eceff1; margin: .75em 0; padding: .5em; border-radius: 5px; }}
    .conversation-info {{
      background-color: #fafafa;
      padding: 0.5em;
      margin-bottom: 0.5em;
      border-left: 4px solid #ccc;
      font-size: 0.9em;
    }}
    .metadata-section {{
      background: #fefefe;
      border: 1px solid #eee;
      margin-top: 0.75em;
      padding: 0.5em;
      border-radius: 4px;
    }}
    hr {{ border: none; border-top: 1px dashed #ccc; margin: 2em 0; }}
    pre {{ background: #f5f5f5; padding: .5em; border-radius: 5px; overflow: auto; }}
    img {{ max-width: 100%; height: auto; }}
    code {{ background: #f5f5f5; padding: 0.2em 0.4em; border-radius: 3px; }}
    em, i {{ font-style: italic; }}
    .message-content {{ margin-top: 0.5em; }}
    .color-key {{
      margin-top: 2em;
      padding: 1em;
      border-top: 2px solid #ccc;
    }}
    .color-key span {{
      display: inline-block;
      margin-right: 1em;
      padding: 0.2em 0.5em;
      border-radius: 3px;
    }}
    .collection-header {{
      margin: 2em 0 1em 0;
      padding: 0.5em;
      background: #f5f5f5;
      border-left: 5px solid #2196F3;
    }}
  </style>
  <script>
    MathJax = {{
      tex: {{
        inlineMath: [["\\\\(","\\\\)"], ["$","$"]],
        displayMath: [["\\\\[","\\\\]"], ["$$","$$"]]
      }},
      options: {{
        skipHtmlTags: ["script","noscript","style","textarea","pre","code"]
      }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body>
  <h1>{title}</h1>
  
  <div class="content">
    {''.join(combined_content)}
  </div>
  
  <div class="color-key">
    <h2>Color Key</h2>
    <span class="role-user">User</span>
    <span class="role-assistant">Assistant</span>
    <span class="role-tool">Tool</span>
    <span class="role-unknown">Unknown</span>
  </div>
</body>
</html>
"""
            
            # Write to file
            output_path.write_text(html_content, encoding="utf-8")
            
            if format == "pdf" and WEASYPRINT_AVAILABLE:
                # Convert HTML to PDF
                pdf_renderer = PDFRenderer()
                pdf_data = pdf_renderer._html_to_pdf(html_content)
                output_path.write_bytes(pdf_data)
            
        typer.echo(f"Combined collections rendered to {output_path}")
    except Exception as e:
        typer.echo(f"Error rendering combined collections: {str(e)}")
        raise typer.Exit(1)

@render_app.command("templates")
def templates_cmd():
    """
    List available rendering templates.
    """
    from carchive.rendering.template_engine import TemplateEngine
    
    template_engine = TemplateEngine()
    templates = template_engine.get_available_templates()
    
    typer.echo("Available templates:")
    for template in templates:
        typer.echo(f"  - {template}")
        
@render_app.command("message")
def message_cmd(
    message_id: str,
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(False, help="Include metadata in the output")
):
    """
    Render a single message to a file in the specified format.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Validate message ID
    try:
        message_uuid = uuid.UUID(message_id)
    except ValueError:
        typer.echo(f"Error: Invalid message ID format: {message_id}")
        raise typer.Exit(1)
    
    # Retrieve message from database
    with get_session() as session:
        message = session.query(Message).filter_by(id=message_id).first()
        if not message:
            typer.echo(f"Error: Message '{message_id}' not found.")
            raise typer.Exit(1)
        
        # Create a rendered item
        rendered_item = {
            "role": message.meta_info.get("author_role", "unknown") if message.meta_info else "unknown",
            "content": renderer.markdown_renderer.render(message.content, message_id),
            "metadata": message.meta_info or {},
            "header": f"Message ID: {message_id}"
        }
        
        # Build context for template
        context = {
            "title": f"Message: {message_id}",
            "items": [rendered_item],
            "include_metadata": include_metadata,
            "show_color_key": True
        }
        
        # Get the template from the template engine
        from carchive.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine()
        
        # Render the template
        html_content = template_engine.render(template, context)
        
        # Output based on format
        if format == "html":
            output_path.write_text(html_content, encoding="utf-8")
        elif format == "pdf":
            pdf_data = renderer._html_to_pdf(html_content)
            output_path.write_bytes(pdf_data)
        
        typer.echo(f"Message {message_id} rendered to {output_path}")

@render_app.command("chunk")
def chunk_cmd(
    chunk_id: str,
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(False, help="Include metadata in the output")
):
    """
    Render a single chunk to a file in the specified format.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Validate chunk ID
    try:
        chunk_uuid = uuid.UUID(chunk_id)
    except ValueError:
        typer.echo(f"Error: Invalid chunk ID format: {chunk_id}")
        raise typer.Exit(1)
    
    # Retrieve chunk from database
    with get_session() as session:
        chunk = session.query(Chunk).filter_by(id=chunk_id).first()
        if not chunk:
            typer.echo(f"Error: Chunk '{chunk_id}' not found.")
            raise typer.Exit(1)
        
        # Create a rendered item
        rendered_item = {
            "role": "unknown",  # Chunks don't have roles
            "content": renderer.markdown_renderer.render(chunk.content),
            "metadata": chunk.meta_info or {},
            "header": f"Chunk ID: {chunk_id}"
        }
        
        # Build context for template
        context = {
            "title": f"Chunk: {chunk_id}",
            "items": [rendered_item],
            "include_metadata": include_metadata,
            "show_color_key": False
        }
        
        # Get the template from the template engine
        from carchive.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine()
        
        # Render the template
        html_content = template_engine.render(template, context)
        
        # Output based on format
        if format == "html":
            output_path.write_text(html_content, encoding="utf-8")
        elif format == "pdf":
            pdf_data = renderer._html_to_pdf(html_content)
            output_path.write_bytes(pdf_data)
        
        typer.echo(f"Chunk {chunk_id} rendered to {output_path}")

@render_app.command("buffer")
def buffer_cmd(
    buffer_name: str,
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(False, help="Include metadata in the output")
):
    """
    Render a buffer's contents to a file in the specified format.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies:")
            typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")
        raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    # Retrieve buffer from database
    with get_session() as session:
        buffer = session.query(Buffer).filter_by(name=buffer_name).first()
        if not buffer:
            typer.echo(f"Error: Buffer '{buffer_name}' not found.")
            raise typer.Exit(1)
        
        # Get buffer items
        buffer_items = session.query(BufferItem).filter_by(buffer_id=buffer.id).all()
        if not buffer_items:
            typer.echo(f"Error: Buffer '{buffer_name}' has no items.")
            raise typer.Exit(1)
        
        rendered_items = []
        
        # Process each buffer item
        for item in buffer_items:
            if item.message_id:
                message = session.query(Message).filter_by(id=item.message_id).first()
                if message:
                    role = message.meta_info.get("author_role", "unknown") if message.meta_info else "unknown"
                    content = renderer.markdown_renderer.render(message.content, str(message.id))
                    metadata = message.meta_info or {}
                    header = f"Message ID: {message.id}"
                    
                    # Add conversation info if available
                    if message.conversation_id:
                        conversation = session.query(Conversation).filter_by(id=message.conversation_id).first()
                        if conversation:
                            header += f" | Conversation: {conversation.title or '(Untitled)'}"
                    
                    rendered_items.append({
                        "role": role,
                        "content": content,
                        "metadata": metadata,
                        "header": header
                    })
            
            elif item.chunk_id:
                chunk = session.query(Chunk).filter_by(id=item.chunk_id).first()
                if chunk:
                    content = renderer.markdown_renderer.render(chunk.content)
                    metadata = chunk.meta_info or {}
                    header = f"Chunk ID: {chunk.id}"
                    
                    rendered_items.append({
                        "role": "unknown",
                        "content": content,
                        "metadata": metadata,
                        "header": header
                    })
        
        if not rendered_items:
            typer.echo(f"Error: No valid content found in buffer '{buffer_name}'.")
            raise typer.Exit(1)
        
        # Build context for template
        context = {
            "title": f"Buffer: {buffer_name}",
            "items": rendered_items,
            "include_metadata": include_metadata,
            "show_color_key": True
        }
        
        # Get the template from the template engine
        from carchive.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine()
        
        # Render the template
        html_content = template_engine.render(template, context)
        
        # Output based on format
        if format == "html":
            output_path.write_text(html_content, encoding="utf-8")
        elif format == "pdf":
            pdf_data = renderer._html_to_pdf(html_content)
            output_path.write_bytes(pdf_data)
        
        typer.echo(f"Buffer '{buffer_name}' rendered to {output_path}")

@render_app.command("media-messages")
def media_messages_cmd(
    limit: int = typer.Option(10, help="Number of media entries to process"),
    media_type: str = typer.Option("image", help="Type of media to filter by (e.g., 'image', 'pdf')"),
    output_file: str = typer.Argument(..., help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(True, help="Include metadata in the output")
):
    """
    Render messages that have associated media files.
    
    This command finds messages that have media attachments and renders them with
    their associated media files displayed inline. Useful for viewing uploaded images
    or AI-generated content.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
            raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    with get_session() as session:
        # Query media with the specified type, ordered by most recent first
        media_query = session.query(Media).filter(Media.media_type == media_type).order_by(Media.created_at.desc()).limit(limit)
        media_entries = media_query.all()
        
        if not media_entries:
            typer.echo(f"No media entries found with type '{media_type}'.")
            raise typer.Exit(1)
        
        typer.echo(f"Found {len(media_entries)} media entries of type '{media_type}'.")
        
        # Prepare data for rendering
        rendered_items = []
        
        for media_entry in media_entries:
            # Find messages associated with this media via MessageMedia table
            media_associations = session.query(MessageMedia).filter(MessageMedia.media_id == media_entry.id).all()
            
            if not media_associations:
                typer.echo(f"No message associations found for media {media_entry.id}, skipping.")
                continue
            
            for assoc in media_associations:
                message = session.query(Message).filter(Message.id == assoc.message_id).first()
                if not message:
                    typer.echo(f"Message {assoc.message_id} not found for media {media_entry.id}, skipping.")
                    continue
                
                # Enhance content with media display
                media_path = media_entry.file_path
                # Convert to absolute URL path using file:// protocol if needed
                media_url = f"file://{os.path.abspath(media_path)}"
                
                # Get message role
                role = message.role
                
                # Create enhanced content with the media embedded
                content = message.content
                
                # Find if the content already references the media and avoid duplicate display
                if media_entry.original_file_id and media_entry.original_file_id in content:
                    # The message already references this media, so replace the reference with actual image markdown
                    # This assumes the content contains the file ID in a format that can be replaced
                    if media_entry.media_type == "image":
                        # Create markdown image tag
                        img_markdown = f"![{media_entry.original_file_name or 'Image'}]({media_url})"
                        # Replace the file reference with the actual image markdown
                        enhanced_content = content.replace(media_entry.original_file_id, img_markdown)
                    else:
                        # For non-images, replace with a link
                        link_markdown = f"[{media_entry.original_file_name or 'File'}]({media_url})"
                        enhanced_content = content.replace(media_entry.original_file_id, link_markdown)
                else:
                    # The message doesn't explicitly reference this media (or it's in a different format)
                    # Add media display at the top of the message
                    if media_entry.media_type == "image":
                        # Use markdown format for images
                        media_markdown = f"![{media_entry.original_file_name or 'Image'}]({media_url})\n\n"
                        enhanced_content = f"{media_markdown}{content}"
                    else:
                        # Use markdown format for other files
                        media_markdown = f"[{media_entry.original_file_name or 'File'}]({media_url})\n\n"
                        enhanced_content = f"{media_markdown}{content}"
                
                # Create metadata object including both message and media metadata
                metadata = {}
                if message.meta_info:
                    metadata["message"] = message.meta_info
                
                metadata["media"] = {
                    "id": str(media_entry.id),
                    "file_path": media_entry.file_path,
                    "media_type": media_entry.media_type,
                    "original_file_name": media_entry.original_file_name,
                    "mime_type": media_entry.mime_type,
                    "file_size": media_entry.file_size,
                    "created_at": str(media_entry.created_at)
                }
                
                # Add to conversation info
                header = f"Message ID: {message.id} | Media ID: {media_entry.id}"
                if message.conversation_id:
                    conversation = session.query(Conversation).filter(Conversation.id == message.conversation_id).first()
                    if conversation:
                        header += f" | Conversation: {conversation.title or '(Untitled)'}"
                
                # Render content with Markdown, passing the message ID for associated media
                rendered_content = renderer.markdown_renderer.render(enhanced_content, str(message.id))
                
                # Add to rendered items
                rendered_items.append({
                    "role": role,
                    "content": rendered_content,
                    "metadata": metadata,
                    "header": header
                })
        
        if not rendered_items:
            typer.echo("No messages with media found to render.")
            raise typer.Exit(1)
        
        # Build context for template
        context = {
            "title": f"Messages with {media_type.capitalize()} Media",
            "items": rendered_items,
            "include_metadata": include_metadata,
            "show_color_key": True
        }
        
        # Get the template from the template engine
        from carchive.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine()
        
        # Render the template
        html_content = template_engine.render(template, context)
        
        # Output based on format
        if format == "html":
            output_path.write_text(html_content, encoding="utf-8")
        elif format == "pdf":
            pdf_data = renderer._html_to_pdf(html_content)
            output_path.write_bytes(pdf_data)
        
        typer.echo(f"Rendered {len(rendered_items)} messages with media to {output_path}")

@render_app.command("media-conversation")
def media_conversation_cmd(
    conversation_id: str,
    output_file: str = typer.Option("media_conversation.html", help="Path to save the output file"),
    format: str = typer.Option("html", help=f"Output format: {', '.join(OUTPUT_FORMATS)}"),
    template: str = typer.Option("default", help="Template to use for rendering"),
    include_metadata: bool = typer.Option(False, help="Include metadata in output")
):
    """
    Render a conversation with all media properly displayed.
    
    This command renders an entire conversation, showing all media attachments inline
    with their associated messages. Helps visualize conversations with uploaded images
    or AI-generated content.
    """
    output_path = Path(output_file)
    
    # Validate format
    format = format.lower()
    if format not in OUTPUT_FORMATS:
        typer.echo(f"Error: Unsupported format '{format}'. Supported formats: {', '.join(OUTPUT_FORMATS)}")
        if format == "pdf" and not WEASYPRINT_AVAILABLE:
            typer.echo("PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
            raise typer.Exit(1)
    
    # Select renderer based on format
    if format == "html":
        renderer = HTMLRenderer()
    elif format == "pdf":
        if not WEASYPRINT_AVAILABLE:
            typer.echo("Error: PDF generation requires WeasyPrint.")
            raise typer.Exit(1)
        renderer = PDFRenderer()
    
    with get_session() as session:
        # Verify conversation exists
        conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            typer.echo(f"Error: Conversation '{conversation_id}' not found.")
            raise typer.Exit(1)
            
        # Get all messages for this conversation in the correct order
        messages = session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        if not messages:
            typer.echo(f"Error: No messages found in conversation '{conversation_id}'.")
            raise typer.Exit(1)
            
        # Prepare data for rendering
        rendered_items = []
        
        for message in messages:
            # Get the message's role and content
            role = message.role
            content = message.content
            
            # Find media associated with this message via MessageMedia table
            media_associations = session.query(MessageMedia).filter(MessageMedia.message_id == message.id).all()
            
            # Enhanced content will have embedded media if there are associations
            enhanced_content = content
            
            # Process each media item
            media_info = []
            for assoc in media_associations:
                media_entry = session.query(Media).filter(Media.id == assoc.media_id).first()
                if not media_entry:
                    typer.echo(f"Media {assoc.media_id} not found for message {message.id}, skipping.")
                    continue
                
                # Get media file URL
                media_path = media_entry.file_path
                media_url = f"file://{os.path.abspath(media_path)}"
                
                # Only add explicit media element if it's not already referenced in the content
                if not (media_entry.original_file_id and media_entry.original_file_id in content):
                    if media_entry.media_type == "image":
                        media_html = f'<div class="media-display"><img src="{media_url}" alt="Media {media_entry.id}" style="max-width:100%;"></div>'
                    else:
                        media_html = f'<div class="media-display"><a href="{media_url}">View Media: {media_entry.original_file_name or media_entry.id}</a></div>'
                    
                    # Add media at the top of the message
                    enhanced_content = f"{media_html}\n\n{enhanced_content}"
                
                # Add media info to metadata
                media_info.append({
                    "id": str(media_entry.id),
                    "media_type": media_entry.media_type,
                    "file_path": media_entry.file_path,
                    "original_file_name": media_entry.original_file_name,
                    "mime_type": media_entry.mime_type
                })
            
            # Create metadata for the message
            metadata = message.meta_info or {}
            if media_info:
                metadata["associated_media"] = media_info
            
            # Render content with Markdown, passing the message ID for associated media
            rendered_content = renderer.markdown_renderer.render(enhanced_content, str(message.id))
            
            # Add to rendered items
            rendered_items.append({
                "role": role,
                "content": rendered_content,
                "metadata": metadata,
                "header": f"Message ID: {message.id}" if include_metadata else None
            })
        
        # Build context for template
        context = {
            "title": f"Conversation: {conversation.title or conversation_id}",
            "items": rendered_items,
            "include_metadata": include_metadata,
            "show_color_key": True
        }
        
        # Get the template engine and render
        from carchive.rendering.template_engine import TemplateEngine
        template_engine = TemplateEngine()
        html_content = template_engine.render(template, context)
        
        # Output based on format
        if format == "html":
            output_path.write_text(html_content, encoding="utf-8")
        elif format == "pdf":
            pdf_data = renderer._html_to_pdf(html_content)
            output_path.write_bytes(pdf_data)
        
        typer.echo(f"Conversation {conversation_id} with media rendered to {output_path}")

@render_app.command("formats")
def formats_cmd():
    """
    List available output formats.
    """
    typer.echo("Available output formats:")
    for format in OUTPUT_FORMATS:
        typer.echo(f"  - {format}")
    
    if "pdf" not in OUTPUT_FORMATS:
        typer.echo("\nPDF format is not available because WeasyPrint is not installed.")
        typer.echo("To enable PDF output, install WeasyPrint and its dependencies:")
        typer.echo("https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation")