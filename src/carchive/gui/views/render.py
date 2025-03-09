"""
GUI views for rendering content.
"""

from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, Response, send_file, abort
import os
import tempfile
import importlib.util
from uuid import UUID

from carchive.database.session import get_session
from carchive.database.models import Collection, Conversation, Message
from carchive.rendering.html_renderer import HTMLRenderer
from carchive.rendering.template_engine import TemplateEngine

# Check if WeasyPrint is available
WEASYPRINT_AVAILABLE = importlib.util.find_spec("weasyprint") is not None
if WEASYPRINT_AVAILABLE:
    from carchive.rendering.pdf_renderer import PDFRenderer

bp = Blueprint('render', __name__, url_prefix='/render')


@bp.route('/')
def render_home():
    """Render home page with options for what to render."""
    # Get available templates
    template_engine = TemplateEngine()
    templates = template_engine.get_available_templates()
    
    # Get available formats
    formats = ['html']
    if WEASYPRINT_AVAILABLE:
        formats.append('pdf')
    
    # Get collections for the dropdown
    with get_session() as session:
        collections = session.query(Collection).order_by(Collection.name).all()
    
    return render_template(
        'render/index.html',
        templates=templates,
        formats=formats,
        collections=collections,
        pdf_available=WEASYPRINT_AVAILABLE
    )


@bp.route('/conversation/<conversation_id>')
def render_conversation(conversation_id):
    """Render a conversation with options."""
    try:
        # Validate UUID format
        try:
            uuid_obj = UUID(conversation_id)
        except ValueError:
            flash("Invalid conversation ID format", "error")
            return redirect(url_for('conversations.list_conversations'))
        
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template_name = request.args.get('template', 'default')
        include_raw = request.args.get('include_raw', 'false').lower() == 'true'
        gencom_fields = request.args.get('gencom_fields', 'none')
        media_display = request.args.get('media_display', 'inline')
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Check if conversation exists
        with get_session() as session:
            conversation = session.query(Conversation).filter_by(id=conversation_id).first()
            
            if not conversation:
                flash(f"Conversation with ID {conversation_id} not found", "error")
                return redirect(url_for('conversations.list_conversations'))
        
        # Process gencom field labels if provided
        field_labels_dict = {}
        gencom_field_labels = request.args.get('gencom_field_labels', '')
        if gencom_field_labels:
            try:
                for mapping in gencom_field_labels.split(','):
                    field, label = mapping.split(':', 1)
                    field_labels_dict[field.strip()] = label.strip()
            except ValueError:
                flash("Invalid format for gencom field labels", "error")
                return redirect(url_for('conversations.view_conversation', conversation_id=conversation_id))
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            flash(f"Unsupported format: {format_type}", "error")
            return redirect(url_for('conversations.view_conversation', conversation_id=conversation_id))
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            flash("PDF format requires WeasyPrint library", "error")
            return redirect(url_for('conversations.view_conversation', conversation_id=conversation_id))
        
        # Validate media display mode
        valid_display_modes = ["inline", "gallery", "thumbnails"]
        if media_display not in valid_display_modes:
            flash(f"Invalid media display mode: {media_display}", "error")
            return redirect(url_for('conversations.view_conversation', conversation_id=conversation_id))
        
        # Set up renderer based on format - use web mode for browser rendering
        # Always use the API port (8000) for media URLs, not the GUI port
        api_base_url = "http://localhost:8000"
            
        if format_type == 'html':
            # Use web mode for HTML rendering
            renderer = HTMLRenderer(web_mode=True, api_url=api_base_url)
        else:  # pdf
            # PDFs need file:// URLs for proper local rendering
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Render the conversation
            renderer.render_conversation(
                conversation_id=conversation_id,
                output_path=output_path,
                template=template_name,
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
            
        except Exception as e:
            current_app.logger.error(f"Error rendering conversation: {e}")
            flash(f"Error rendering conversation: {str(e)}", "error")
            return redirect(url_for('conversations.view_conversation', conversation_id=conversation_id))
            
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
                
    except Exception as e:
        current_app.logger.error(f"Error in render_conversation: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('conversations.list_conversations'))


@bp.route('/collection/<collection_name>')
def render_collection(collection_name):
    """Render a collection with options."""
    try:
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template_name = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'false').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Check if collection exists
        with get_session() as session:
            collection = session.query(Collection).filter_by(name=collection_name).first()
            
            if not collection:
                flash(f"Collection '{collection_name}' not found", "error")
                return redirect(url_for('collections.list_collections'))
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            flash(f"Unsupported format: {format_type}", "error")
            return redirect(url_for('collections.view_collection', collection_name=collection_name))
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            flash("PDF format requires WeasyPrint library", "error")
            return redirect(url_for('collections.view_collection', collection_name=collection_name))
        
        # Set up renderer based on format - use web mode for browser rendering
        # Always use the API port (8000) for media URLs, not the GUI port
        api_base_url = "http://localhost:8000"
            
        if format_type == 'html':
            # Use web mode for HTML rendering
            renderer = HTMLRenderer(web_mode=True, api_url=api_base_url)
        else:  # pdf
            # PDFs need file:// URLs for proper local rendering
            renderer = PDFRenderer()
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Render the collection
            renderer.render_collection(
                collection_name=collection_name,
                output_path=output_path,
                template=template_name,
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
            
        except Exception as e:
            current_app.logger.error(f"Error rendering collection: {e}")
            flash(f"Error rendering collection: {str(e)}", "error")
            return redirect(url_for('collections.view_collection', collection_name=collection_name))
            
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
                
    except Exception as e:
        current_app.logger.error(f"Error in render_collection: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('collections.list_collections'))


@bp.route('/message/<message_id>')
def render_message(message_id):
    """Render a single message with options."""
    try:
        # Validate UUID format
        try:
            uuid_obj = UUID(message_id)
        except ValueError:
            flash("Invalid message ID format", "error")
            return redirect(url_for('messages.list_messages'))
        
        # Get query parameters
        format_type = request.args.get('format', 'html').lower()
        template_name = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'false').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Check if message exists
        with get_session() as session:
            message = session.query(Message).filter_by(id=message_id).first()
            
            if not message:
                flash(f"Message with ID {message_id} not found", "error")
                return redirect(url_for('messages.list_messages'))
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            flash(f"Unsupported format: {format_type}", "error")
            return redirect(url_for('messages.view_message', message_id=message_id))
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            flash("PDF format requires WeasyPrint library", "error")
            return redirect(url_for('messages.view_message', message_id=message_id))
        
        # Create a temporary file to hold the output
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
            output_path = temp_file.name
        
        try:
            # Set up renderer based on format
            if format_type == 'html':
                renderer = HTMLRenderer()
            else:  # pdf
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
            html_content = template_engine.render(template_name, context)
            
            # Output based on format
            if format_type == 'html':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            elif format_type == 'pdf':
                pdf_data = renderer._html_to_pdf(html_content)
                with open(output_path, 'wb') as f:
                    f.write(pdf_data)
            
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
            
        except Exception as e:
            current_app.logger.error(f"Error rendering message: {e}")
            flash(f"Error rendering message: {str(e)}", "error")
            return redirect(url_for('messages.view_message', message_id=message_id))
            
        finally:
            # Clean up the temporary file after response is sent
            if os.path.exists(output_path):
                os.unlink(output_path)
                
    except Exception as e:
        current_app.logger.error(f"Error in render_message: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('messages.list_messages'))


@bp.route('/combined', methods=['GET', 'POST'])
def render_combined():
    """Render multiple collections into a single file."""
    # Get collections for the dropdown
    with get_session() as session:
        collections = session.query(Collection).order_by(Collection.name).all()
    
    # Get available templates
    template_engine = TemplateEngine()
    templates = template_engine.get_available_templates()
    
    # Get available formats
    formats = ['html']
    if WEASYPRINT_AVAILABLE:
        formats.append('pdf')
    
    # Handling the form submission
    if request.method == 'POST':
        try:
            # Get form data
            selected_collections = request.form.getlist('collections')
            title = request.form.get('title', '')
            format_type = request.form.get('format', 'html').lower()
            template_name = request.form.get('template', 'default')
            download = request.form.get('download', 'false').lower() == 'true'
            
            if not selected_collections:
                flash("Please select at least one collection", "error")
                return render_template(
                    'render/combined.html',
                    collections=collections,
                    templates=templates,
                    formats=formats,
                    pdf_available=WEASYPRINT_AVAILABLE
                )
            
            # Validate format
            if format_type not in ['html', 'pdf']:
                flash(f"Unsupported format: {format_type}", "error")
                return render_template(
                    'render/combined.html',
                    collections=collections,
                    templates=templates,
                    formats=formats,
                    pdf_available=WEASYPRINT_AVAILABLE
                )
            
            if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
                flash("PDF format requires WeasyPrint library", "error")
                return render_template(
                    'render/combined.html',
                    collections=collections,
                    templates=templates,
                    formats=formats,
                    pdf_available=WEASYPRINT_AVAILABLE
                )
            
            # Set up renderer based on format
            if format_type == 'html':
                renderer = HTMLRenderer()
            else:  # pdf
                renderer = PDFRenderer()
            
            # Create a temporary file to hold the output
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format_type}') as temp_file:
                output_path = temp_file.name
            
            try:
                # Verify collections exist
                with get_session() as session:
                    for coll_name in selected_collections:
                        if not session.query(Collection).filter_by(name=coll_name).first():
                            flash(f"Collection '{coll_name}' not found", "error")
                            return render_template(
                                'render/combined.html',
                                collections=collections,
                                templates=templates,
                                formats=formats,
                                pdf_available=WEASYPRINT_AVAILABLE
                            )
                
                # Generate title if not provided
                if not title:
                    title = f"Combined Collections: {', '.join(selected_collections)}"
                
                # Render combined collections
                combined_content = []
                
                for collection_name in selected_collections:
                    # For HTML, we'll render each collection separately and combine
                    collection_content = renderer.render_collection(
                        collection_name=collection_name,
                        output_path=None,  # Don't write to file yet
                        template=template_name,
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
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    if format_type == 'pdf' and WEASYPRINT_AVAILABLE:
                        # Convert HTML to PDF
                        pdf_renderer = PDFRenderer()
                        pdf_data = pdf_renderer._html_to_pdf(html_content)
                        with open(output_path, 'wb') as f:
                            f.write(pdf_data)
                
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
                
            except Exception as e:
                current_app.logger.error(f"Error rendering combined collections: {e}")
                flash(f"Error rendering combined collections: {str(e)}", "error")
                return render_template(
                    'render/combined.html',
                    collections=collections,
                    templates=templates,
                    formats=formats,
                    pdf_available=WEASYPRINT_AVAILABLE
                )
                
            finally:
                # Clean up the temporary file after response is sent
                if os.path.exists(output_path):
                    os.unlink(output_path)
                    
        except Exception as e:
            current_app.logger.error(f"Error in render_combined: {e}")
            flash(f"Error: {str(e)}", "error")
            return render_template(
                'render/combined.html',
                collections=collections,
                templates=templates,
                formats=formats,
                pdf_available=WEASYPRINT_AVAILABLE
            )
    
    # Display the form for GET requests
    return render_template(
        'render/combined.html',
        collections=collections,
        templates=templates,
        formats=formats,
        pdf_available=WEASYPRINT_AVAILABLE
    )


@bp.route('/media-messages')
def render_media_messages():
    """Render messages with media files."""
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 10))
        media_type = request.args.get('media_type', 'image')
        format_type = request.args.get('format', 'html').lower()
        template_name = request.args.get('template', 'default')
        include_metadata = request.args.get('include_metadata', 'true').lower() == 'true'
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Validate format
        if format_type not in ['html', 'pdf']:
            flash(f"Unsupported format: {format_type}", "error")
            return redirect(url_for('render.render_home'))
        
        if format_type == 'pdf' and not WEASYPRINT_AVAILABLE:
            flash("PDF format requires WeasyPrint library", "error")
            return redirect(url_for('render.render_home'))
        
        # Create API request to the render media messages endpoint
        api_url = url_for('render.render_media_messages', _external=True)
        api_url += f"?limit={limit}&media_type={media_type}&format={format_type}&template={template_name}"
        api_url += f"&include_metadata={'true' if include_metadata else 'false'}&download={'true' if download else 'false'}"
        
        # Redirect to the API endpoint
        return redirect(api_url)
        
    except Exception as e:
        current_app.logger.error(f"Error in render_media_messages: {e}")
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('render.render_home'))


@bp.route('/templates')
def list_templates():
    """List available templates."""
    try:
        template_engine = TemplateEngine()
        templates = template_engine.get_available_templates()
        
        return render_template(
            'render/templates.html',
            templates=templates
        )
        
    except Exception as e:
        current_app.logger.error(f"Error listing templates: {e}")
        flash(f"Error listing templates: {str(e)}", "error")
        return redirect(url_for('render.render_home'))