"""
Media routes for the carchive GUI.
"""

import requests
import logging
import os
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify, send_file, abort
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
bp = Blueprint('media', __name__, url_prefix='/media')

@bp.route('/')
def list_media():
    """List media files with pagination and filtering."""
    # Get request parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    media_type = request.args.get('type', 'image')  # Default to showing images
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    is_generated = request.args.get('is_generated')
    
    # Validate parameters
    if per_page > 100:
        per_page = 100  # Limit maximum per page
        
    # Get API URLs from config
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    try:
        # First check API health
        health_response = requests.get(f"{api_base_url}/health", timeout=2)
        health_response.raise_for_status()
        
        # Build API request parameters
        params = {
            'page': page,
            'per_page': per_page,
            'type': media_type,
            'sort': sort_by,
            'order': sort_order
        }
        
        # Add optional parameters if provided
        if is_generated:
            params['is_generated'] = is_generated
            
        # Get media list from API
        media_url = f"{api_base_url}/media/"
        response = requests.get(media_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Get available media types for filtering
        types_response = requests.get(f"{api_base_url}/media/types", timeout=3)
        types_response.raise_for_status()
        media_types = types_response.json().get('types', [])
        
        # Build pagination info
        pagination = data.get('pagination', {
            'page': page,
            'per_page': per_page,
            'total': 0,
            'pages': 0
        })
        
        # Process media items to include preview URLs
        media_items = data.get('media', [])
        for item in media_items:
            # Add direct URL to preview the media
            item['preview_url'] = f"{api_base_url}/media/{item['id']}/file"
            
            # Add URL to view the media detail page
            item['detail_url'] = url_for('media.view_media', media_id=item['id'], _external=True)
            
            # For better user experience, add file type icons based on media_type
            if item['media_type'] == 'image':
                item['icon'] = 'image'
            elif item['media_type'] == 'audio':
                item['icon'] = 'volume-up'
            elif item['media_type'] == 'video':
                item['icon'] = 'film'
            elif item['media_type'] == 'pdf':
                item['icon'] = 'file-pdf'
            else:
                item['icon'] = 'file'
        
        # Render the template with data
        return render_template(
            'media/list.html',
            media_items=media_items,
            pagination=pagination,
            media_types=media_types,
            current_type=media_type,
            current_sort=sort_by,
            current_order=sort_order,
            current_is_generated=is_generated
        )
        
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error fetching media: {str(e)}")
        return render_template(
            'media/list.html',
            media_items=[],
            pagination={'page': page, 'per_page': per_page, 'total': 0, 'pages': 0},
            media_types=[],
            current_type=media_type,
            api_error=f"Error: {str(e)}"
        )

@bp.route('/<media_id>')
def view_media(media_id):
    """View a single media file with its details and associated messages."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    logger = logging.getLogger(__name__)
    logger.info(f"Viewing media details for: {media_id} using API URL: {api_url}")
    
    try:
        # Get media details from API with comprehensive debug logging
        media_endpoint = f"{api_base_url}/media/{media_id}"
        logger.debug(f"Requesting media from API: {media_endpoint}")
        
        # Get media details from API
        response = requests.get(media_endpoint, timeout=5)
        
        # Log response status and headers for debugging
        logger.debug(f"API response status: {response.status_code}")
        logger.debug(f"API response headers: {response.headers}")
        
        # Check if response is valid with detailed error logging
        if response.status_code != 200:
            logger.error(f"API returned non-200 status: {response.status_code}")
            logger.error(f"Response content: {response.text[:500]}")
            return render_template(
                'media/view.html',
                media={'id': media_id, 'error': f"API returned status {response.status_code}"},
                associated_messages=[],
                api_error=f"API Error: Status {response.status_code}",
                api_url=api_url
            )
            
        # Parse response as JSON with comprehensive error handling
        try:
            media = response.json()
            if hasattr(media, 'keys'):
                logger.debug(f"Media data structure: keys={list(media.keys())}")
            else:
                logger.error(f"Media response is not a dictionary: {type(media)}")
                return render_template(
                    'media/view.html',
                    media={'id': media_id, 'error': "Invalid response format (not a dictionary)"},
                    associated_messages=[],
                    api_error=f"API Response Error: Expected dictionary, got {type(media)}",
                    api_url=api_url
                )
        except Exception as json_error:
            logger.error(f"Failed to parse API response as JSON: {str(json_error)}")
            logger.error(f"Response content: {response.text[:500]}")
            return render_template(
                'media/view.html',
                media={'id': media_id, 'error': "Invalid API response format"},
                associated_messages=[],
                api_error=f"API Response Error: {str(json_error)}",
                api_url=api_url
            )
        
        # Validate required fields with detailed logging
        if not isinstance(media, dict):
            logger.error(f"Media response is not a dictionary: {type(media)}")
            return render_template(
                'media/view.html',
                media={'id': media_id, 'error': "Invalid response format"},
                associated_messages=[],
                api_error="API Response Error: Not a dictionary",
                api_url=api_url
            )
            
        if 'id' not in media:
            logger.error(f"Media response missing ID field: {media}")
            return render_template(
                'media/view.html',
                media={'id': media_id, 'error': "Media response missing ID field"},
                associated_messages=[],
                api_error="API Response Error: Missing ID field",
                api_url=api_url
            )
        
        # Add direct file URLs for preview
        media['file_url'] = f"{api_base_url}/media/{media['id']}/file"
        media['thumbnail_url'] = f"{api_base_url}/media/{media['id']}/thumbnail"
        logger.debug(f"Added file_url: {media['file_url']}")
        logger.debug(f"Added thumbnail_url: {media['thumbnail_url']}")
        
        # Safely process associated messages with comprehensive error handling
        associated_messages = []
        
        # Process uploader message if present
        if isinstance(media.get('uploader_message'), dict):
            try:
                uploader_message = media['uploader_message']
                uploader_message['role'] = 'uploader'
                # Safely create URL only if ID exists
                if 'id' in uploader_message:
                    uploader_message['url'] = url_for('messages.view_message', message_id=uploader_message['id'])
                    if 'conversation_id' in uploader_message:
                        uploader_message['conversation_url'] = url_for(
                            'conversations.view_conversation', 
                            conversation_id=uploader_message['conversation_id']
                        )
                    associated_messages.append(uploader_message)
                    logger.debug(f"Added uploader message with ID: {uploader_message['id']}")
                else:
                    logger.warning(f"Uploader message missing ID: {uploader_message}")
            except Exception as msg_error:
                logger.error(f"Error processing uploader message: {str(msg_error)}")
                logger.error(f"Uploader message content: {media.get('uploader_message')}")
        
        # Process linked message if present
        if isinstance(media.get('linked_message'), dict):
            try:
                linked_message = media['linked_message']
                linked_message['role'] = 'linked'
                # Safely create URL only if ID exists
                if 'id' in linked_message:
                    linked_message['url'] = url_for('messages.view_message', message_id=linked_message['id'])
                    if 'conversation_id' in linked_message:
                        linked_message['conversation_url'] = url_for(
                            'conversations.view_conversation', 
                            conversation_id=linked_message['conversation_id']
                        )
                    associated_messages.append(linked_message)
                    logger.debug(f"Added linked message with ID: {linked_message['id']}")
                else:
                    logger.warning(f"Linked message missing ID: {linked_message}")
            except Exception as msg_error:
                logger.error(f"Error processing linked message: {str(msg_error)}")
                logger.error(f"Linked message content: {media.get('linked_message')}")
        
        # Log successful processing before rendering
        logger.info(f"Successfully processed media {media_id}, rendering template with {len(associated_messages)} associated messages")
        
        # Render template with enhanced error handling
        return render_template(
            'media/view.html',
            media=media,
            associated_messages=associated_messages,
            api_url=api_url,  # Pass API URL to template
            api_base_url=api_base_url  # Pass API base URL for direct file access
        )
        
    except requests.RequestException as req_error:
        # Handle API connection errors with detailed logging
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Request error when fetching media: {str(req_error)}")
        logger.error(error_details)
        
        return render_template(
            'media/view.html',
            media={'id': media_id, 'error': str(req_error)},
            associated_messages=[],
            api_error=f"API Connection Error: {str(req_error)}",
            api_url=api_url,
            debug_info=error_details if current_app.config.get('DEBUG', False) else None
        )
        
    except Exception as e:
        # Handle any other errors with comprehensive error info
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Unexpected error in view_media: {str(e)}")
        logger.error(error_details)
        
        # Log additional context for debugging
        try:
            logger.debug(f"Context - Media ID: {media_id}")
            logger.debug(f"Context - API URL: {api_url}")
            logger.debug(f"Context - API Base URL: {api_base_url}")
            logger.debug(f"Context - Request headers: {getattr(response, 'request', {}).headers if 'response' in locals() else 'N/A'}")
        except Exception as log_err:
            logger.error(f"Error logging debug context: {str(log_err)}")
            
        return render_template(
            'media/view.html',
            media={'id': media_id, 'error': str(e)},
            associated_messages=[],
            api_error=f"Unexpected Error: {str(e)}",
            api_url=api_url,
            debug_info=error_details if current_app.config.get('DEBUG', False) else None
        )


@bp.route('/debug/<media_id>')
def debug_media(media_id):
    """Debug view for media items with path issues."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    logger = logging.getLogger(__name__)
    logger.info(f"DEBUG: Analyzing media item {media_id}")
    
    try:
        # Get basic media details
        media_response = requests.get(f"{api_base_url}/media/{media_id}", timeout=5)
        media_response.raise_for_status()
        media = media_response.json()
        
        # Get file path debug info
        path_debug_response = requests.get(f"{api_base_url}/media/{media_id}/file/debug", timeout=5)
        path_debug_response.raise_for_status()
        path_info = path_debug_response.json()
        
        # Check if the media file exists
        file_exists = False
        working_path = None
        all_paths = []
        
        for path_test in path_info.get('path_tests', []):
            all_paths.append(path_test)
            if path_test.get('exists', False) and path_test.get('readable', False):
                file_exists = True
                working_path = path_test.get('path')
                break
        
        # Additional checks
        file_url = f"{api_base_url}/media/{media_id}/file"
        try:
            # Do a HEAD request to check if file is accessible via API
            file_head = requests.head(file_url, timeout=3)
            file_accessible = file_head.status_code == 200
            file_content_type = file_head.headers.get('Content-Type')
            file_size = file_head.headers.get('Content-Length')
        except:
            file_accessible = False
            file_content_type = None
            file_size = None
        
        # Render the debug template
        return render_template(
            'media/debug.html',
            media=media,
            path_info=path_info,
            file_exists=file_exists,
            working_path=working_path,
            all_paths=all_paths,
            file_accessible=file_accessible,
            file_content_type=file_content_type,
            file_size=file_size,
            file_url=file_url,
            media_id=media_id,
            api_url=api_url
        )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in debug_media: {str(e)}")
        logger.error(error_details)
        
        return render_template(
            'media/debug.html',
            error=str(e),
            traceback=error_details,
            media_id=media_id,
            api_url=api_url
        )

@bp.route('/file/<media_id>')
def serve_media_file(media_id):
    """Proxy the media file from the API."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    
    try:
        # Get media details to determine content type
        media_response = requests.get(f"{api_url}/api/media/{media_id}", timeout=5)
        media_response.raise_for_status()
        media = media_response.json()
        
        # Determine content type based on media_type
        content_type = None
        if media.get('media_type') == 'image':
            content_type = 'image/jpeg'  # Default for images
            file_path = media.get('file_path', '')
            if file_path.lower().endswith('.png'):
                content_type = 'image/png'
            elif file_path.lower().endswith('.gif'):
                content_type = 'image/gif'
            elif file_path.lower().endswith('.webp'):
                content_type = 'image/webp'
        elif media.get('media_type') == 'pdf':
            content_type = 'application/pdf'
        elif media.get('media_type') == 'audio':
            content_type = 'audio/mpeg'
        
        # Get the file from the API
        file_response = requests.get(f"{api_url}/api/media/{media_id}/file", stream=True, timeout=10)
        file_response.raise_for_status()
        
        # Return the file directly (streaming)
        return (file_response.content, file_response.status_code, {
            'Content-Type': content_type or file_response.headers.get('Content-Type', 'application/octet-stream'),
            'Content-Disposition': f'inline; filename="{media.get("original_file_name", media_id)}"'
        })
    
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error serving media file: {str(e)}")
        abort(404, description=f"Media file not found: {str(e)}")

@bp.route('/by-conversation/<conversation_id>')
def list_media_by_conversation(conversation_id):
    """List media files associated with a specific conversation."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    api_base_url = current_app.config.get('API_BASE_URL', f"{api_url}/api")
    
    logger = logging.getLogger(__name__)
    logger.info(f"Getting media for conversation: {conversation_id}")
    
    try:
        # Get conversation details first
        conversation_response = requests.get(f"{api_base_url}/conversations/{conversation_id}", timeout=5)
        conversation_response.raise_for_status()
        conversation = conversation_response.json()
        
        # Get messages in the conversation
        messages_response = requests.get(
            f"{api_base_url}/messages/?conversation_id={conversation_id}&per_page=100", 
            timeout=5
        )
        messages_response.raise_for_status()
        messages_data = messages_response.json()
        
        # Collect all media items from messages
        media_items = []
        for message in messages_data.get('messages', []):
            # Check for attached media (newer association method)
            if message.get('media_items'):
                for media in message.get('media_items', []):
                    # Add message context to the media item
                    media['message_id'] = message.get('id')
                    media['message_role'] = message.get('role', 'unknown')
                    media['message_content'] = message.get('content', '')[:100] + '...' if message.get('content') and len(message.get('content')) > 100 else message.get('content', '')
                    media['preview_url'] = f"{api_base_url}/media/{media['id']}/file"
                    media['detail_url'] = url_for('media.view_media', media_id=media['id'])
                    media_items.append(media)
            
            # Check for media in message.media (legacy/compatibility)
            if message.get('media'):
                media = message.get('media')
                # Add message context to the media item
                media['message_id'] = message.get('id')
                media['message_role'] = message.get('role', 'unknown')
                media['message_content'] = message.get('content', '')[:100] + '...' if message.get('content') and len(message.get('content')) > 100 else message.get('content', '')
                media['preview_url'] = f"{api_base_url}/media/{media['id']}/file"
                media['detail_url'] = url_for('media.view_media', media_id=media['id'])
                media_items.append(media)
        
        # Render template with media items
        return render_template(
            'media/conversation_media.html',
            conversation=conversation,
            media_items=media_items
        )
        
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Error fetching conversation media: {str(e)}")
        return render_template(
            'media/conversation_media.html',
            conversation={'id': conversation_id, 'title': 'Unknown Conversation'},
            media_items=[],
            api_error=f"Error: {str(e)}"
        )