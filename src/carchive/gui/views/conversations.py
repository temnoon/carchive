"""
Conversation routes for the carchive GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('conversations', __name__, url_prefix='/conversations')

@bp.route('/')
def list_conversations():
    """List conversations with pagination and filtering."""
    api_url = current_app.config['API_URL']
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    title_filter = request.args.get('title', '')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build API URL with query parameters
    api_endpoint = f"{api_url}/api/conversations"
    params = {
        'page': page,
        'per_page': per_page,
        'sort': sort_by,
        'order': sort_order
    }
    
    if title_filter:
        params['title'] = title_filter
    
    try:
        response = requests.get(api_endpoint, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            conversations = data.get('conversations', [])
            pagination = data.get('pagination', {})
        else:
            error_msg = f"Error retrieving conversations: {response.status_code}"
            logger.error(error_msg)
            flash(error_msg, "error")
            return render_template(
                'conversations/list.html',
                title_filter=title_filter,
                sort_by=sort_by,
                sort_order=sort_order,
                api_error=True,
                error_message=error_msg
            )
    except requests.RequestException as e:
        error_msg = f"Error connecting to API: {str(e)}"
        logger.error(error_msg)
        flash(error_msg, "error")
        return render_template(
            'conversations/list.html',
            title_filter=title_filter,
            sort_by=sort_by,
            sort_order=sort_order,
            api_error=True,
            error_message=error_msg
        )
    
    return render_template(
        'conversations/list.html',
        conversations=conversations,
        pagination=pagination,
        title_filter=title_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@bp.route('/<conversation_id>')
def view_conversation(conversation_id):
    """View a single conversation with its messages."""
    api_url = current_app.config['API_URL']
    
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    show_gencom = request.args.get('gencom', 'true').lower() in ('true', 'yes', '1')
    
    # Request conversation data from API
    api_endpoint = f"{api_url}/api/conversations/{conversation_id}"
    params = {
        'include_messages': 'true',
        'page': page,
        'per_page': per_page
    }
    
    try:
        response = requests.get(api_endpoint, params=params, timeout=15)
        if response.status_code == 200:
            conversation = response.json()
            messages = conversation.get('messages', [])
            pagination = conversation.get('pagination', {})
            
            # Process messages to properly handle media
            has_media = False
            for message in messages:
                try:
                    # Check for media items in the message
                    message_has_media = False
                    
                    # Handle media items array
                    if 'media_items' in message and message['media_items']:
                        message_has_media = True
                        has_media = True
                        
                        # Process each media item to include direct preview URLs
                        for media_item in message['media_items']:
                            if 'id' in media_item:
                                media_item['preview_url'] = f"{api_url}/api/media/{media_item['id']}/file"
                                
                    # Handle single media item (legacy/compatibility)
                    if 'media' in message and message['media'] and isinstance(message['media'], dict):
                        message_has_media = True
                        has_media = True
                        
                        # Add direct URL for preview
                        if 'id' in message['media']:
                            message['media']['preview_url'] = f"{api_url}/api/media/{message['media']['id']}/file"
                            
                    # Process DALL-E asset references in messages and add properly processed content
                    if 'content' in message and message['content']:
                        if isinstance(message['content'], str):
                            # Import required modules
                            import os
                            import re
                            from carchive.rendering.markdown_renderer import MarkdownRenderer
                            from carchive.database.session import get_session
                            from carchive.database.models import Media
                            
                            # Process message content with markdown renderer that uses API URLs
                            try:
                                # Create a web-mode markdown renderer that uses API URLs
                                # Make sure to use port 8000 (API) not 8001 (GUI)
                                api_base_url = "http://localhost:8000"
                                web_renderer = MarkdownRenderer(web_mode=True, api_url=api_base_url)
                                
                                with get_session() as session:
                                    # Process embedded images with our web-mode renderer
                                    processed_content = web_renderer.process_embedded_images(
                                        message['content'], 
                                        message_id=message.get('id'),
                                        session=session
                                    )
                                    
                                    # Render the processed content to HTML
                                    html_content = web_renderer.render(processed_content, message.get('id'))
                                    
                                    # Final safety check: replace any remaining file:// URLs in the rendered HTML
                                    def replace_file_url(match):
                                        file_path = match.group(1)
                                        
                                        try:
                                            # Extract just the filename without path
                                            filename = os.path.basename(file_path)
                                            
                                            # Try to find media entry with matching path or filename
                                            media = session.query(Media).filter(
                                                (Media.file_path == file_path) | 
                                                (Media.file_path.like(f'%{filename}%'))
                                            ).first()
                                            
                                            if media:
                                                return f'src="{api_url}/api/media/{media.id}/file"'
                                            
                                            # Fallback if not found
                                            return f'src="{api_url}/api/media/not-found"'
                                        except Exception as e:
                                            logger.error(f"Error processing file URL {file_path}: {e}")
                                            return f'src="{api_url}/api/media/error"'
                                    
                                    # Replace all file:// URLs in the HTML
                                    html_content = re.sub(r'src="file://([^"]+)"', replace_file_url, html_content)
                                    
                                    # Store the fully processed content
                                    message['processed_content'] = html_content
                                    
                                    # Check if this message has media references
                                    if 'Asset: file-' in message['content']:
                                        message_has_media = True
                                        has_media = True
                            except Exception as e:
                                logger.error(f"Error processing markdown for message {message.get('id')}: {e}")
                                # Leave content as-is if there's an error
                except Exception as e:
                    # Log the error but continue processing
                    logger.error(f"Error processing media for message {message.get('id', 'unknown')}: {str(e)}")
                    message_has_media = False
                        
                # If message has any media, set a flag for the template
                message['has_media'] = message_has_media
                
            # Add a media flag to the conversation for the template
            conversation['has_media'] = has_media
            
            # If gencom is enabled, fetch agent outputs for each message
            if show_gencom and messages:
                message_ids = [message['id'] for message in messages]
                gencom_data = _fetch_gencom_for_messages(api_url, message_ids)
                
                # Attach gencom data to messages
                for message in messages:
                    message_id = message['id']
                    if message_id in gencom_data:
                        message['gencom'] = gencom_data[message_id]
        else:
            error_msg = f"Error retrieving conversation: {response.status_code}"
            logger.error(error_msg)
            flash(error_msg, "error")
            # Show sample conversation with error notice
            return render_template(
                'conversations/view.html',
                conversation={
                    'id': conversation_id,
                    'title': 'Error Loading Conversation',
                    'created_at': None,
                    'updated_at': None,
                    'model': 'Unknown'
                },
                messages=[],
                pagination={'page': 1, 'pages': 1, 'total': 0},
                api_error=True,
                error_message=error_msg,
                show_gencom=False,
                api_url=api_url
            )
    except requests.RequestException as e:
        error_msg = f"Error connecting to API: {str(e)}"
        logger.error(error_msg)
        flash(error_msg, "error")
        # Show sample conversation with error notice
        return render_template(
            'conversations/view.html',
            conversation={
                'id': conversation_id,
                'title': 'Error Loading Conversation',
                'created_at': None,
                'updated_at': None,
                'model': 'Unknown'
            },
            messages=[],
            pagination={'page': 1, 'pages': 1, 'total': 0},
            api_error=True,
            error_message=error_msg,
            show_gencom=False,
            api_url=api_url
        )
    
    # Process the HTML to fix any file:// URLs 
    from flask import render_template_string
    import os
    import re
    from carchive.database.session import get_session
    from carchive.database.models import Media
    
    # First render the template
    html = render_template(
        'conversations/view.html',
        conversation=conversation,
        messages=messages,
        pagination=pagination,
        show_gencom=show_gencom,
        api_url=api_url
    )
    
    # Now fix any file:// URLs in the generated HTML
    with get_session() as session:
        def replace_file_url(match):
            file_path = match.group(1)
            
            try:
                # Extract just the filename without path
                filename = os.path.basename(file_path)
                
                # Query the database for media with matching filename in file_path
                media = None
                
                # Try exact match first
                media = session.query(Media).filter(Media.file_path == file_path).first()
                
                # If not found, try partial match with LIKE
                if not media and filename:
                    media = session.query(Media).filter(Media.file_path.like(f'%{filename}%')).first()
                
                # If found, use API URL with media ID
                if media:
                    return f'src="{api_url}/api/media/{media.id}/file"'
                
                # If still not found by path, try original_file_name
                if filename:
                    media = session.query(Media).filter(Media.original_file_name == filename).first()
                    if media:
                        return f'src="{api_url}/api/media/{media.id}/file"'
                
                # As a last resort, look for UUID in the path that might match media ID
                import uuid
                try:
                    # Try to extract something that looks like a UUID from the path
                    pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
                    uuid_match = re.search(pattern, file_path)
                    if uuid_match:
                        possible_uuid = uuid_match.group(0)
                        media = session.query(Media).filter(Media.id == possible_uuid).first()
                        if media:
                            return f'src="{api_url}/api/media/{media.id}/file"'
                except:
                    pass
                
                # Fallback if not found
                logger.warning(f"Could not find media for file: {file_path}")
                return f'src="{api_url}/api/media/not-found"'
            except Exception as e:
                logger.error(f"Error processing file URL {file_path}: {e}")
                return f'src="{api_url}/api/media/error"'
        
        # Replace all file:// URLs in the HTML
        html = re.sub(r'src="file://([^"]+)"', replace_file_url, html)
        
        # Also replace any direct file references not in src attributes
        html = re.sub(r'file://([^\s"\'<>]+)', lambda m: f"{api_url}/api/media/path/{m.group(1)}", html)
    
    # Return the fixed HTML
    return render_template_string(html)
    
@bp.route('/<conversation_id>/media')
def conversation_media(conversation_id):
    """View media files in a conversation."""
    return redirect(url_for('media.list_media_by_conversation', conversation_id=conversation_id))

def _fetch_gencom_for_messages(api_url, message_ids):
    """
    Fetch gencom data for a list of message IDs.
    Returns a dictionary mapping message IDs to their gencom data.
    """
    if not message_ids:
        return {}
    
    # Prepare results dictionary
    gencom_data = {}
    
    try:
        # Make parallel API requests for each message ID
        for message_id in message_ids:
            api_endpoint = f"{api_url}/api/messages/{message_id}/gencom"
            response = requests.get(api_endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'outputs' in data and data['outputs']:
                    gencom_data[message_id] = data['outputs']
    except requests.RequestException as e:
        logger.error(f"Error fetching gencom data: {str(e)}")
    
    return gencom_data