"""
API endpoints for search functionality.
"""

from typing import Dict, List, Optional, Any, Tuple
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, func, or_, cast, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload, Session
import json

from carchive.database.models import Conversation, Message, Media, Embedding
from carchive.api.schemas import ConversationBase, MessageBase, MediaBase, SearchResult
from carchive.api.routes.utils import (
    db_session, parse_pagination_params, error_response
)

bp = Blueprint('search', __name__, url_prefix='/api/search')


@bp.route('/', methods=['GET'])
@db_session
def search(session: Session):
    """Search conversations, messages, and media."""
    # Get search parameters
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')  # 'all', 'conversations', 'messages', 'media'
    page, per_page = parse_pagination_params()
    
    # Validate search type
    valid_types = ['all', 'conversations', 'messages', 'media']
    if search_type not in valid_types:
        return error_response(400, f"Invalid search type. Must be one of: {', '.join(valid_types)}")
    
    # Initialize result counters
    total_conversations = 0
    total_messages = 0
    total_media = 0
    
    # Initialize result lists
    conversations = []
    messages = []
    media = []
    
    # If query is empty, return empty results
    if not query:
        return jsonify(SearchResult().dict())
    
    # Search conversations
    if search_type in ['all', 'conversations']:
        conv_query = session.query(Conversation).filter(
            or_(
                Conversation.title.ilike(f'%{query}%'),
                cast(Conversation.meta_info, JSONB).contains({"summary": f"%{query}%"})
            )
        ).order_by(desc(Conversation.created_at))
        
        if search_type == 'conversations':
            # Apply pagination if only searching conversations
            conversations, total_conversations = paginate_query(conv_query, page, per_page)
        else:
            # Just get counts if searching all
            total_conversations = conv_query.count()
            if total_conversations > 0:
                conversations = conv_query.limit(min(5, total_conversations)).all()
    
    # Search messages
    if search_type in ['all', 'messages']:
        msg_query = session.query(Message).filter(
            Message.content.ilike(f'%{query}%')
        ).options(joinedload(Message.media)).order_by(desc(Message.created_at))
        
        if search_type == 'messages':
            # Apply pagination if only searching messages
            messages, total_messages = paginate_query(msg_query, page, per_page)
        else:
            # Just get counts if searching all
            total_messages = msg_query.count()
            if total_messages > 0:
                messages = msg_query.limit(min(5, total_messages)).all()
    
    # Search media
    if search_type in ['all', 'media']:
        media_query = session.query(Media).filter(
            or_(
                Media.file_name.ilike(f'%{query}%'),
                Media.original_file_id.ilike(f'%{query}%')
            )
        ).order_by(desc(Media.created_at))
        
        if search_type == 'media':
            # Apply pagination if only searching media
            media, total_media = paginate_query(media_query, page, per_page)
        else:
            # Just get counts if searching all
            total_media = media_query.count()
            if total_media > 0:
                media = media_query.limit(min(5, total_media)).all()
    
    # Format response
    result = {
        'query': query,
        'type': search_type,
        'conversations': [ConversationBase.from_orm(conv).dict() for conv in conversations],
        'messages': [MessageBase.from_orm(msg).dict() for msg in messages],
        'media': [MediaBase.from_orm(m).dict() for m in media],
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'total_media': total_media,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': {
                'conversations': total_conversations if search_type == 'conversations' else None,
                'messages': total_messages if search_type == 'messages' else None,
                'media': total_media if search_type == 'media' else None,
                'all': total_conversations + total_messages + total_media if search_type == 'all' else None
            }
        }
    }
    
    return jsonify(result)


@bp.route('/vector', methods=['GET', 'POST'])
@db_session
def vector_search(session: Session):
    """Perform vector search using embeddings."""
    # Get search parameters from either query params or JSON body
    if request.method == 'GET':
        query = request.args.get('q', '')
        embedding_model = request.args.get('model', 'default')
        limit = request.args.get('limit', 10, type=int)
    else:  # POST
        data = request.get_json() or {}
        query = data.get('query', '')
        embedding_model = data.get('model', 'default')
        limit = data.get('limit', 10)
    
    # Validate query
    if not query:
        return error_response(400, "Query parameter is required")
    
    # TODO: Implement actual vector search using embeddings
    # This is a placeholder that just does a text search for now
    
    # Search messages
    messages = session.query(Message).filter(
        Message.content.ilike(f'%{query}%')
    ).options(joinedload(Message.media)).order_by(desc(Message.created_at)).limit(limit).all()
    
    # Format response
    result = {
        'query': query,
        'model': embedding_model,
        'results': [
            {
                'message': MessageBase.from_orm(msg).dict(),
                'score': 0.5,  # Placeholder similarity score
                'conversation_id': str(msg.conversation_id)
            }
            for msg in messages
        ]
    }
    
    return jsonify(result)


@bp.route('/save', methods=['POST'])
@db_session
def save_search(session: Session):
    """Save a search query for future reference."""
    # Get parameters
    data = request.get_json() or {}
    
    query = data.get('query')
    name = data.get('name')
    search_type = data.get('type', 'all')
    
    # Validate required fields
    if not query:
        return error_response(400, "Query parameter is required")
    if not name:
        return error_response(400, "Name parameter is required")
    
    # TODO: Implement saving search criteria to database
    # This is a placeholder
    
    return jsonify({
        'success': True,
        'name': name,
        'query': query,
        'type': search_type,
        'id': 'placeholder-id'  # Placeholder ID
    })