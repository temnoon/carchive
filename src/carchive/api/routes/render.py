"""
API endpoints for rendering conversations, collections, messages, and other content.
"""

from typing import Dict, List, Optional, Any, Union
from flask import Blueprint, request, jsonify, current_app, Response, send_file
from sqlalchemy import desc, func, or_, cast, text
from sqlalchemy.orm import Session
import json
import os
import tempfile
from pathlib import Path
from uuid import UUID
import importlib.util

from carchive.database.models import Collection, CollectionItem, Message, Conversation, Chunk, Media, MessageMedia
from carchive.database.session import get_session, db_session
from carchive.api.routes.utils import db_session, parse_pagination_params, error_response
from carchive.rendering.html_renderer import HTMLRenderer
from carchive.rendering.template_engine import TemplateEngine

# Check if WeasyPrint is available
WEASYPRINT_AVAILABLE = importlib.util.find_spec("weasyprint") is not None
if WEASYPRINT_AVAILABLE:
    from carchive.rendering.pdf_renderer import PDFRenderer

bp = Blueprint('render', __name__, url_prefix='/api/render')


@bp.route('/conversation/<conversation_id>', methods=['GET'])
@db_session
def render_conversation(session: Session, conversation_id: str):
    """
    Render a conversation to HTML or PDF.
    
    Query parameters:
    - format: 'html' (default) or 'pdf'
    - template: template name (default: 'default')
    - include_raw: include raw markdown (default: false)
    - gencom_fields: which gencom fields to include (default: 'none')
    - gencom_field_labels: mapping of field names to display labels (default: '')
    - media_display: media display mode (default: 'inline')
    - download: whether to force download (default: false)
    """
    try:
        # Validate UUID format
        try:
            uuid_obj = UUID(conversation_id)
        except ValueError:
            return error_response(400, "Invalid conversation ID format")
        
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template = request.args.get('template', 'default')
        include_raw = request.args.get('include_raw', 'false').lower() == 'true'
        gencom_fields = request.args.get('gencom_fields', 'none')
        media_display = request.args.get('media_display', 'inline')
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Process gencom field labels if provided
        field_labels_dict = {}
        gencom_field_labels = request.args.get('gencom_field_labels', '')
        if gencom_field_labels:
            try:
                for mapping in gencom_field_labels.split(','):
                    field, label = mapping.split(':', 1)
                    field_labels_dict[field.strip()] = label.strip()
            except ValueError:
                return error_response(400, "Invalid format for gencom field labels. Use 'field:Label,another:Another Label'")
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            return error_response(400, f"Unsupported format '{format_type}'. Supported formats: html, pdf")
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            return error_response(400, "PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
        
        # Validate media display mode
        valid_display_modes = ["inline", "gallery", "thumbnails"]
        if media_display not in valid_display_modes:
            return error_response(400, f"Invalid media display mode '{media_display}'. Valid modes: {', '.join(valid_display_modes)}")
        
        # Check if conversation exists
        conversation = session.query(Conversation).filter_by(id=conversation_id).first()
        if not conversation:
            return error_response(404, f"Conversation '{conversation_id}' not found")
        
        # Set up renderer based on format
        if format_type == 'html':
            renderer = HTMLRenderer()
        else:  # pdf
            if not WEASYPRINT_AVAILABLE:
                return error_response(400, "PDF generation requires WeasyPrint.")
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Render the conversation
            renderer.render_conversation(
                conversation_id=conversation_id,
                output_path=output_path,
                template=template,
                include_raw=include_raw,
                gencom_fields=gencom_fields,
                gencom_field_labels=field_labels_dict,
                media_display_mode=media_display
            )
            
            # Set the appropriate content type
            content_type = 'text/html' if format_type == 'html' else 'application/pdf'
            
            # Set filename for download
            filename = f"conversation_{conversation_id}.{format_type}"
            
            # Return the file
            return send_file(
                output_path,
                mimetype=content_type,
                as_attachment=download,
                download_name=filename
            )
        
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering conversation: {e}")
        return error_response(500, f"Error rendering conversation: {str(e)}")


@bp.route('/collection/<collection_name>', methods=['GET'])
@db_session
def render_collection(session: Session, collection_name: str):
    """
    Render a collection to HTML or PDF.
    
    Query parameters:
    - format: 'html' (default) or 'pdf'
    - template: template name (default: 'default')
    - include_metadata: include metadata in output (default: false)
    - download: whether to force download (default: false)
    """
    try:
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'false').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            return error_response(400, f"Unsupported format '{format_type}'. Supported formats: html, pdf")
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            return error_response(400, "PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
        
        # Check if collection exists
        collection = session.query(Collection).filter_by(name=collection_name).first()
        if not collection:
            return error_response(404, f"Collection '{collection_name}' not found")
        
        # Set up renderer based on format
        if format_type == 'html':
            renderer = HTMLRenderer()
        else:  # pdf
            if not WEASYPRINT_AVAILABLE:
                return error_response(400, "PDF generation requires WeasyPrint.")
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Render the collection
            renderer.render_collection(
                collection_name=collection_name,
                output_path=output_path,
                template=template,
                include_metadata=include_metadata
            )
            
            # Set the appropriate content type
            content_type = 'text/html' if format_type == 'html' else 'application/pdf'
            
            # Set filename for download
            filename = f"collection_{collection_name}.{format_type}"
            
            # Return the file
            return send_file(
                output_path,
                mimetype=content_type,
                as_attachment=download,
                download_name=filename
            )
        
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering collection: {e}")
        return error_response(500, f"Error rendering collection: {str(e)}")


@bp.route('/message/<message_id>', methods=['GET'])
@db_session
def render_message(session: Session, message_id: str):
    """
    Render a single message to HTML or PDF.
    
    Query parameters:
    - format: 'html' (default) or 'pdf'
    - template: template name (default: 'default')
    - include_metadata: include metadata in output (default: false)
    - download: whether to force download (default: false)
    """
    try:
        # Validate UUID format
        try:
            message_uuid = UUID(message_id)
        except ValueError:
            return error_response(400, "Invalid message ID format")
        
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'false').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            return error_response(400, f"Unsupported format '{format_type}'. Supported formats: html, pdf")
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            return error_response(400, "PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
        
        # Check if message exists
        message = session.query(Message).filter_by(id=message_id).first()
        if not message:
            return error_response(404, f"Message '{message_id}' not found")
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Set up renderer based on format
            if format_type == 'html':
                renderer = HTMLRenderer()
            else:  # pdf
                if not WEASYPRINT_AVAILABLE:
                    return error_response(400, "PDF generation requires WeasyPrint.")
                renderer = PDFRenderer()
            
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
            template_engine = TemplateEngine()
            
            # Render the template
            html_content = template_engine.render(template, context)
            
            # Output based on format
            if format_type == 'html':
                Path(output_path).write_text(html_content, encoding="utf-8")
            elif format_type == 'pdf':
                pdf_data = renderer._html_to_pdf(html_content)
                Path(output_path).write_bytes(pdf_data)
            
            # Set the appropriate content type
            content_type = 'text/html' if format_type == 'html' else 'application/pdf'
            
            # Set filename for download
            filename = f"message_{message_id}.{format_type}"
            
            # Return the file
            return send_file(
                output_path,
                mimetype=content_type,
                as_attachment=download,
                download_name=filename
            )
        
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering message: {e}")
        return error_response(500, f"Error rendering message: {str(e)}")


@bp.route('/combined', methods=['POST'])
@db_session
def render_combined(session: Session):
    """
    Render multiple collections into a single file.
    
    Body parameters:
    - collections: List of collection names to render
    - title: Custom title for the combined output (optional)
    
    Query parameters:
    - format: 'html' (default) or 'pdf'
    - template: template name (default: 'default')
    - download: whether to force download (default: false)
    """
    try:
        # Get body parameters
        data = request.get_json() or {}
        
        if 'collections' not in data or not data['collections']:
            return error_response(400, "Collections list is required")
        
        collections = data['collections']
        title = data.get('title')
        
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template = request.args.get('template', 'default')
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            return error_response(400, f"Unsupported format '{format_type}'. Supported formats: html, pdf")
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            return error_response(400, "PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
        
        # Verify collections exist
        for coll_name in collections:
            if not session.query(Collection).filter_by(name=coll_name).first():
                return error_response(404, f"Collection '{coll_name}' not found")
        
        # Generate title if not provided
        if not title:
            title = f"Combined Collections: {', '.join(collections)}"
        
        # Select renderer based on format
        if format_type == 'html':
            renderer = HTMLRenderer()
        else:  # pdf
            if not WEASYPRINT_AVAILABLE:
                return error_response(400, "PDF generation requires WeasyPrint.")
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Render combined collections
            combined_content = []
            
            for collection_name in collections:
                # For HTML, we'll render each collection separately and combine
                collection_content = renderer.render_collection(
                    collection_name=collection_name,
                    output_path=None,  # Don't write to file yet
                    template=template,
                    include_metadata=False
                )
                
                if format_type == 'html':
                    # Extract just the content part for HTML
                    start_marker = "<div class=\"content\">"
                    end_marker = "</div>\n  \n  <div class=\"color-key\">"
                    start_idx = collection_content.find(start_marker)
                    end_idx = collection_content.find(end_marker)
                    
                    if start_idx >= 0 and end_idx >= 0:
                        content_part = collection_content[start_idx + len(start_marker):end_idx]
                        combined_content.append(content_part)
            
            # Create combined output
            if format_type == 'html':
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
                Path(output_path).write_text(html_content, encoding="utf-8")
                
                if format_type == 'pdf' and WEASYPRINT_AVAILABLE:
                    # Convert HTML to PDF
                    pdf_renderer = PDFRenderer()
                    pdf_data = pdf_renderer._html_to_pdf(html_content)
                    Path(output_path).write_bytes(pdf_data)
                
            # Set the appropriate content type
            content_type = 'text/html' if format_type == 'html' else 'application/pdf'
            
            # Set filename for download
            filename = f"combined_collections.{format_type}"
            
            # Return the file
            return send_file(
                output_path,
                mimetype=content_type,
                as_attachment=download,
                download_name=filename
            )
        
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering combined collections: {e}")
        return error_response(500, f"Error rendering combined collections: {str(e)}")


@bp.route('/media-messages', methods=['GET'])
@db_session
def render_media_messages(session: Session):
    """
    Render messages that have associated media files.
    
    Query parameters:
    - limit: Number of media entries to process (default: 10)
    - media_type: Type of media to filter by (default: 'image')
    - format: 'html' (default) or 'pdf'
    - template: template name (default: 'default')
    - include_metadata: include metadata in output (default: true)
    - download: whether to force download (default: false)
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 10))
        media_type = request.args.get('media_type', 'image')
        format_type = request.args.get('format', 'html').lower()
        template = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'true').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            return error_response(400, f"Unsupported format '{format_type}'. Supported formats: html, pdf")
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            return error_response(400, "PDF format requires WeasyPrint. Please install WeasyPrint and its dependencies.")
        
        # Select renderer based on format
        if format_type == 'html':
            renderer = HTMLRenderer()
        else:  # pdf
            if not WEASYPRINT_AVAILABLE:
                return error_response(400, "PDF generation requires WeasyPrint.")
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        # Query media with the specified type, ordered by most recent first
        media_query = session.query(Media).filter(Media.media_type == media_type).order_by(Media.created_at.desc()).limit(limit)
        media_entries = media_query.all()
        
        if not media_entries:
            return error_response(404, f"No media entries found with type '{media_type}'")
        
        try:
            # Prepare data for rendering
            rendered_items = []
            
            for media_entry in media_entries:
                # Find messages associated with this media via MessageMedia table
                media_associations = session.query(MessageMedia).filter(MessageMedia.media_id == media_entry.id).all()
                
                if not media_associations:
                    continue
                
                for assoc in media_associations:
                    message = session.query(Message).filter(Message.id == assoc.message_id).first()
                    if not message:
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
                return error_response(404, "No messages with media found to render")
            
            # Build context for template
            context = {
                "title": f"Messages with {media_type.capitalize()} Media",
                "items": rendered_items,
                "include_metadata": include_metadata,
                "show_color_key": True
            }
            
            # Get the template from the template engine
            template_engine = TemplateEngine()
            
            # Render the template
            html_content = template_engine.render(template, context)
            
            # Output based on format
            if format_type == 'html':
                Path(output_path).write_text(html_content, encoding="utf-8")
            elif format_type == 'pdf':
                pdf_data = renderer._html_to_pdf(html_content)
                Path(output_path).write_bytes(pdf_data)
            
            # Set the appropriate content type
            content_type = 'text/html' if format_type == 'html' else 'application/pdf'
            
            # Set filename for download
            filename = f"media_messages_{media_type}.{format_type}"
            
            # Return the file
            return send_file(
                output_path,
                mimetype=content_type,
                as_attachment=download,
                download_name=filename
            )
        
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    except Exception as e:
        current_app.logger.error(f"Error rendering media messages: {e}")
        return error_response(500, f"Error rendering media messages: {str(e)}")


@bp.route('/templates', methods=['GET'])
def list_templates():
    """
    List available rendering templates.
    """
    try:
        from carchive.rendering.template_engine import TemplateEngine
        
        template_engine = TemplateEngine()
        templates = template_engine.get_available_templates()
        
        return jsonify({
            'templates': templates
        })
    
    except Exception as e:
        current_app.logger.error(f"Error listing templates: {e}")
        return error_response(500, f"Error listing templates: {str(e)}")


@bp.route('/formats', methods=['GET'])
def list_formats():
    """
    List available output formats.
    """
    try:
        formats = ['html']
        if WEASYPRINT_AVAILABLE:
            formats.append('pdf')
        
        return jsonify({
            'formats': formats,
            'pdf_available': WEASYPRINT_AVAILABLE
        })
    
    except Exception as e:
        current_app.logger.error(f"Error listing formats: {e}")
        return error_response(500, f"Error listing formats: {str(e)}")