"""
Conversation routes for the carchive2 GUI.
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
                error_message=error_msg
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
            error_message=error_msg
        )
    
    return render_template(
        'conversations/view.html',
        conversation=conversation,
        messages=messages,
        pagination=pagination
    )