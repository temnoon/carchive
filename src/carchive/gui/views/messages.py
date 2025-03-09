"""
Message routes for the carchive GUI.
"""

import requests
from flask import Blueprint, render_template, current_app, request, redirect, url_for, flash, jsonify
import logging
import json
import re
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
bp = Blueprint('messages', __name__, url_prefix='/messages')

def detect_role(message):
    """
    Extract role information from a message's meta_info in a consistent way.
    Returns one of: 'user', 'assistant', 'system', 'tool', or 'unknown'
    """
    if not message or not isinstance(message, dict):
        return 'unknown'
        
    # Check meta_info for role information
    if 'meta_info' in message and message['meta_info']:
        meta = message['meta_info']
        
        # Check for explicit sender field
        if meta.get('sender'):
            sender = meta.get('sender').lower()
            if sender == 'human':
                return 'user'
            return sender  # assistant, system, tool
            
        # Check for metadata.author.role (ChatGPT format)
        if meta.get('metadata') and isinstance(meta['metadata'], dict):
            metadata = meta['metadata']
            if metadata.get('author') and isinstance(metadata['author'], dict):
                author = metadata['author']
                if author.get('role'):
                    return author['role']
                    
            # Check for message_type
            if metadata.get('message_type'):
                msg_type = metadata.get('message_type').lower()
                if 'human' in msg_type:
                    return 'user'
                if 'assistant' in msg_type:
                    return 'assistant'
        
        # Check for channel-specific patterns
        if meta.get('channel') == 'anthropic':
            # Use content patterns to guess the role for Anthropic
            if 'content' in message:
                content = message.get('content', '')
                if content and isinstance(content, str):
                    if ('Exploring' in content or '**' in content or 
                        content.startswith('I') or content.startswith('Here')):
                        return 'assistant'
                    return 'user'
    
    # If we couldn't determine the role, return unknown
    return 'unknown'

@bp.route('/test')
def test_endpoint():
    """Simple test endpoint to verify basic routing."""
    return "The messages test endpoint is working!"
    
@bp.route('/test-api')
def test_api_endpoint():
    """Test endpoint that just attempts to connect to the API."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    
    try:
        health_response = requests.get(f"{api_url}/api/health", timeout=2)
        status_code = health_response.status_code
        health_text = health_response.text
        return f"Connected to API. Status code: {status_code}, Response: {health_text}"
    except Exception as e:
        return f"Error connecting to API: {str(e)}"
        
@bp.route('/json-test')
def json_test():
    """Return message data as JSON for debugging."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    
    try:
        # Get the first 2 messages only
        response = requests.get(f"{api_url}/api/messages/?page=1&per_page=2", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Return as JSON for browser debugging
        return jsonify({
            'status': 'success',
            'message_count': len(data.get('messages', [])),
            'first_message_keys': list(data.get('messages', [{}])[0].keys()) if data.get('messages') else [],
            'message_sample': data.get('messages', [])[:1]  # Just return the first message
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        })
    
@bp.route('/minimal')
def minimal_template_test():
    """Test endpoint with minimal template to verify template rendering."""
    return render_template('messages/minimal.html')
    
@bp.route('/safe-list')
def safe_list_messages():
    """A simplified version of list_messages that should not fail."""
    try:
        return render_template(
            'messages/minimal.html'
        )
    except Exception as e:
        # Log the exception
        logger.error(f"Error in safe_list_messages: {str(e)}")
        # Return a simple string response
        return f"An error occurred: {str(e)}"

@bp.route('/')
def list_messages():
    """Main route for message listing page."""
    # Just redirect to the real list implementation
    return redirect(url_for('messages.real_list'))

@bp.route('/ultra-simple')
def ultra_simple_list():
    """An extremely simplified message list with minimal logic for debugging."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    
    try:
        # Simply check if the API is alive
        health_response = requests.get(f"{api_url}/api/health", timeout=2)
        health_response.raise_for_status()
        
        # Get the first few messages
        response = requests.get(f"{api_url}/api/messages/?page=1&per_page=10", timeout=5)
        response.raise_for_status()
        data = response.json()
        messages = data.get('messages', [])
        
        # Log message structure for debugging
        if messages:
            logger.info(f"First message keys: {list(messages[0].keys())}")
            logger.info(f"First message meta_info: {messages[0].get('meta_info', {})}")
        
        # Build a very simple HTML response manually
        html = "<html><head><title>Ultra Simple Message List</title></head><body>"
        html += "<h1>Ultra Simple Message List</h1>"
        html += f"<p>Connected to API successfully!</p>"
        html += f"<p>Found {len(messages)} messages</p>"
        
        # Add messages
        for msg in messages[:5]:  # Show only first 5 messages
            html += "<div style='border: 1px solid #ccc; padding: 10px; margin-bottom: 10px;'>"
            html += f"<h3>Message ID: {msg.get('id', 'No ID')}</h3>"
            html += f"<p><strong>Created:</strong> {msg.get('created_at', 'Unknown')}</p>"
            
            # Safely truncate content
            content = msg.get('content', 'No content')
            if content and len(content) > 150:
                content = content[:150] + "..."
            
            html += f"<div><strong>Content:</strong> {content}</div>"
            
            # Add metadata section
            html += "<details><summary>View Metadata</summary>"
            html += f"<pre>{str(msg.get('meta_info', {}))}</pre>"
            html += "</details>"
            
            # Add links
            html += "<p>"
            html += f"<a href='/messages/view/{msg.get('id')}'>View Full Message</a> | "
            html += f"<a href='/conversations/view/{msg.get('conversation_id')}'>View Conversation</a>"
            html += "</p>"
            html += "</div>"
        
        # Add footer
        html += "<p><a href='/' style='display: inline-block; padding: 10px; background-color: #007bff; color: white; text-decoration: none;'>Back to Home</a></p>"
        html += "</body></html>"
        
        return html
        
    except Exception as e:
        # Add more detailed error handling
        import traceback
        error_message = f"Error: {str(e)}\n\n"
        error_message += traceback.format_exc()
        logger.error(f"Ultra simple view error: {error_message}")
        return f"<html><body><h1>Error</h1><pre>{error_message}</pre></body></html>"

@bp.route('/real')
def real_list():
    """Ultra simple implementation of message list using working template."""
    # Get search parameters
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Handle gencom toggle properly - this checks if the form was submitted
    gencom_submitted = request.args.get('gencom_submitted', 'false').lower() == 'true'
    if gencom_submitted:
        # If form was submitted, use the value of gencom checkbox
        show_gencom = request.args.get('gencom', 'false').lower() == 'true'
    else:
        # Default to true if not submitted
        show_gencom = True
        
    show_meta = request.args.get('meta', 'false').lower() == 'true'
    
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    
    try:
        # First check API health
        health_response = requests.get(f"{api_url}/api/health", timeout=2)
        health_response.raise_for_status()
        
        # Get messages - simplified approach with minimal error points
        if query:
            # Use search API - debug the search parameters
            logger.info(f"====== STARTING SEARCH FOR: '{query}' ======")
            
            # Use the working search API endpoint used by the CLI
            try:
                # Use the messages search endpoint directly with the content filter parameter
                # This replicates how search_messages() works in CLI
                search_url = f"{api_url}/api/messages/"
                
                search_params = {
                    'content': query,  # This parameter matches Message.content.ilike(f'%{query}%') in API
                    'page': page,
                    'per_page': per_page
                }
                
                logger.info(f"Search URL: {search_url}")
                logger.info(f"Search params: {search_params}")
                
                response = requests.get(search_url, params=search_params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Process the results
                messages = []
                if 'messages' in data:
                    raw_messages = data.get('messages', [])
                    logger.info(f"Found {len(raw_messages)} messages")
                    
                    for item in raw_messages:
                        if not item or not isinstance(item, dict):
                            continue
                            
                        # Ensure item has required fields to prevent template errors
                        if 'id' not in item:
                            logger.warning(f"Message without ID found in search results, skipping")
                            continue
                            
                        # Add empty meta_info if missing
                        if 'meta_info' not in item or item['meta_info'] is None:
                            item['meta_info'] = {}
                        
                        # Add highlighted content for search results
                        if 'content' in item:
                            # Create a simple highlighting by wrapping the search term in <em> tags
                            query_lower = query.lower()
                            content = item['content']
                            
                            # Find index of the match
                            start_idx = content.lower().find(query_lower)
                            if start_idx >= 0:
                                # Get a context snippet
                                start = max(0, start_idx - 100)
                                end = min(len(content), start_idx + len(query) + 100)
                                
                                # Extract the snippet
                                snippet = content[start:end]
                                
                                # Highlight the query term
                                highlight_pattern = re.compile(re.escape(query), re.IGNORECASE)
                                highlighted = highlight_pattern.sub(r'<em>\g<0></em>', snippet)
                                
                                # Add ellipsis if we're not showing the full content
                                if start > 0:
                                    highlighted = "..." + highlighted
                                if end < len(content):
                                    highlighted += "..."
                                    
                                item['highlighted_content'] = highlighted
                        
                        # Check if message has gencom data (without loading it)
                        try:
                            has_gencom_response = requests.head(
                                f"{api_url}/api/messages/{item['id']}/gencom", 
                                timeout=1
                            )
                            item['has_gencom'] = has_gencom_response.status_code == 200
                        except Exception:
                            # Default to false if check fails
                            item['has_gencom'] = False
                            
                        messages.append(item)
                    
                    # Use pagination info from the response
                    pagination = data.get('pagination', {})
                    if not pagination:
                        # Calculate pagination manually if missing
                        total = len(messages)
                        pages = (total + per_page - 1) // per_page if per_page > 0 else 1
                        pagination = {
                            'page': page,
                            'per_page': per_page,
                            'total': total,
                            'pages': pages
                        }
                else:
                    logger.error("Search response has unexpected format")
                    # Create empty results
                    pagination = {
                        'page': page,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 0
                    }
            except Exception as e:
                logger.error(f"Search failed: {str(e)}")
                # Try fallback to search endpoint if messages endpoint fails
                try:
                    logger.info("Using fallback search endpoint")
                    fallback_url = f"{api_url}/api/search/"
                    fallback_params = {
                        'q': query,
                        'type': 'messages',  # Only search messages
                        'page': page,
                        'per_page': per_page
                    }
                    
                    logger.info(f"Fallback search URL: {fallback_url}")
                    logger.info(f"Fallback search params: {fallback_params}")
                    
                    fallback_response = requests.get(fallback_url, params=fallback_params, timeout=10)
                    fallback_response.raise_for_status()
                    fallback_data = fallback_response.json()
                    
                    # Process the fallback results
                    messages = []
                    if 'messages' in fallback_data:
                        raw_messages = fallback_data.get('messages', [])
                        logger.info(f"Fallback search found {len(raw_messages)} messages")
                        
                        for item in raw_messages:
                            if not item or not isinstance(item, dict):
                                continue
                                
                            # Ensure item has required fields to prevent template errors
                            if 'id' not in item:
                                logger.warning(f"Message without ID found in search results, skipping")
                                continue
                                
                            # Add empty meta_info if missing
                            if 'meta_info' not in item or item['meta_info'] is None:
                                item['meta_info'] = {}
                            
                            # Add highlighted content for search results
                            if 'content' in item:
                                # Create a simple highlighting by wrapping the search term in <em> tags
                                query_lower = query.lower()
                                content = item['content']
                                
                                # Find index of the match
                                start_idx = content.lower().find(query_lower)
                                if start_idx >= 0:
                                    # Get a context snippet
                                    start = max(0, start_idx - 100)
                                    end = min(len(content), start_idx + len(query) + 100)
                                    
                                    # Extract the snippet
                                    snippet = content[start:end]
                                    
                                    # Highlight the query term
                                    highlight_pattern = re.compile(re.escape(query), re.IGNORECASE)
                                    highlighted = highlight_pattern.sub(r'<em>\g<0></em>', snippet)
                                    
                                    # Add ellipsis if we're not showing the full content
                                    if start > 0:
                                        highlighted = "..." + highlighted
                                    if end < len(content):
                                        highlighted += "..."
                                        
                                    item['highlighted_content'] = highlighted
                            
                            # Check if message has gencom data (without loading it)
                            try:
                                has_gencom_response = requests.head(
                                    f"{api_url}/api/messages/{item['id']}/gencom", 
                                    timeout=1
                                )
                                item['has_gencom'] = has_gencom_response.status_code == 200
                            except Exception:
                                # Default to false if check fails
                                item['has_gencom'] = False
                                
                            messages.append(item)
                        
                        # Calculate pagination
                        total = fallback_data.get('total_messages', len(messages))
                        pages = (total + per_page - 1) // per_page if per_page > 0 else 1
                        pagination = {
                            'page': page,
                            'per_page': per_page,
                            'total': total,
                            'pages': pages
                        }
                    else:
                        logger.error("Fallback search has unexpected format")
                        # Create empty results
                        pagination = {
                            'page': page,
                            'per_page': per_page,
                            'total': 0,
                            'pages': 0
                        }
                except Exception as e2:
                    logger.error(f"Fallback search also failed: {str(e2)}")
                    # If all attempts fail, return an empty response
                    messages = []
                    pagination = {
                        'page': page,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 0
                    }
                
            logger.info(f"====== COMPLETED SEARCH FOR: '{query}' ======")
            logger.info(f"Search returned {len(messages)} results")
            
            # Log pagination info for debugging
            try:
                logger.info(f"Pagination: page {pagination['page']} of {pagination['pages']}, showing {len(messages)} of {pagination['total']} total results")
            except Exception as e:
                logger.error(f"Error logging pagination: {str(e)}")
        else:
            # Just get list of messages
            messages_url = f"{api_url}/api/messages/"
            params = {
                'page': page,
                'per_page': per_page
            }
            response = requests.get(messages_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            raw_messages = data.get('messages', [])
            
            # Filter and process messages to ensure they have required fields
            messages = []
            for item in raw_messages:
                if not item or not isinstance(item, dict):
                    logger.warning("Non-dict message item found, skipping")
                    continue
                    
                # Ensure message has ID
                if 'id' not in item:
                    logger.warning(f"Message without ID found, skipping")
                    continue
                    
                # Add empty meta_info if missing
                if 'meta_info' not in item or item['meta_info'] is None:
                    item['meta_info'] = {}
                
                # Check if message has gencom data (without loading it)
                try:
                    has_gencom_response = requests.head(
                        f"{api_url}/api/messages/{item['id']}/gencom", 
                        timeout=1
                    )
                    item['has_gencom'] = has_gencom_response.status_code == 200
                except Exception:
                    # Default to false if check fails
                    item['has_gencom'] = False
                    
                messages.append(item)
                
            pagination = data.get('pagination', {})
        
        # Log the first message structure for debugging
        if messages and len(messages) > 0:
            first_msg = messages[0]
            logger.info(f"Message keys: {list(first_msg.keys())}")
        
        # Return the simplified template
        return render_template(
            'messages/simple_list.html',
            messages=messages,
            pagination=pagination,
            query=query,
            role=None,
            show_gencom=show_gencom,
            show_meta=show_meta
        )
        
    except Exception as e:
        # Comprehensive error handling
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"Message list error: {error_msg}")
        
        # Return error message with simple template
        return render_template(
            'messages/simple_list.html',
            messages=[],
            pagination={'page': page, 'per_page': per_page, 'total': 0, 'pages': 0},
            query=query,
            role=None,
            show_gencom=show_gencom,
            show_meta=show_meta,
            api_error=f"Error fetching messages: {str(e)}"
        )

@bp.route('/view/<message_id>')
def view_message(message_id):
    """View a single message with its media."""
    api_url = current_app.config.get('API_URL', 'http://localhost:8000')
    show_gencom = request.args.get('gencom', 'true').lower() == 'true'
    
    try:
        # Get message details
        response = requests.get(f"{api_url}/api/messages/{message_id}")
        response.raise_for_status()
        message = response.json()
        
        # Get message context (previous and next messages)
        context_response = requests.get(f"{api_url}/api/messages/{message_id}/context")
        context_response.raise_for_status()
        context = context_response.json()
        
        # Get gencom data if requested
        if show_gencom:
            try:
                gencom_response = requests.get(f"{api_url}/api/messages/{message_id}/gencom")
                gencom_response.raise_for_status()
                gencom_data = gencom_response.json()
                
                if gencom_data.get('outputs'):
                    message['has_gencom'] = True
                    message['gencom'] = gencom_data.get('outputs', [])
                else:
                    message['has_gencom'] = False
                    message['gencom'] = []
            except Exception as e:
                logger.error(f"Error fetching gencom: {e}")
                message['has_gencom'] = False
                message['gencom'] = []
        
        return render_template(
            'messages/view.html',
            message=message,
            context=context,
            show_gencom=show_gencom
        )
        
    except requests.RequestException as e:
        logger.error(f"API error: {e}")
        return render_template(
            'messages/view.html',
            message=None,
            context=None,
            show_gencom=show_gencom,
            api_error=str(e)
        )