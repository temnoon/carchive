"""
API endpoints for messages.
"""

from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, abort
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload, Session

from carchive.database.models import Message, Media, Conversation
from carchive.api.schemas import MessageBase, MessageDetail, MediaBase
from carchive.api.routes.utils import (
    db_session, validate_uuid, parse_pagination_params, 
    paginate_query, error_response
)

bp = Blueprint('messages', __name__, url_prefix='/api/messages')


@bp.route('/', methods=['GET'])
@db_session
def get_messages(session: Session):
    """Get a list of messages with pagination and filtering."""
    page, per_page = parse_pagination_params()
    
    # Get query filters
    conversation_id = request.args.get('conversation_id')
    content_filter = request.args.get('content')
    role_filter = request.args.get('role')
    has_media = request.args.get('has_media', '').lower()
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = session.query(Message).options(joinedload(Message.media_items))
    
    # Apply filters
    if conversation_id:
        if not validate_uuid(conversation_id):
            return error_response(400, "Invalid conversation ID format")
        query = query.filter(Message.conversation_id == conversation_id)
    
    if content_filter:
        query = query.filter(Message.content.ilike(f'%{content_filter}%'))
    
    if role_filter:
        # Role is stored in meta_info.author_role
        query = query.filter(Message.meta_info['author_role'].astext == role_filter)
    
    if has_media == 'true':
        # Use media_items relationship for filtering
        query = query.join(MessageMedia, Message.id == MessageMedia.message_id).distinct()
    elif has_media == 'false':
        # Subquery approach to find messages without media
        subquery = session.query(MessageMedia.message_id)
        query = query.filter(~Message.id.in_(subquery))
    
    # Apply sorting
    if sort_order.lower() == 'asc':
        query = query.order_by(getattr(Message, sort_by))
    else:
        query = query.order_by(desc(getattr(Message, sort_by)))
    
    # Paginate results
    messages, total = paginate_query(query, page, per_page)
    
    # Format response
    formatted_messages = []
    for msg in messages:
        msg_dict = MessageDetail.from_orm(msg).dict()
        # Replace media with media_items for compatibility
        if hasattr(msg, 'media_items') and msg.media_items:
            msg_dict['media'] = MediaBase.from_orm(msg.media_items[0]).dict() if msg.media_items else None
        formatted_messages.append(msg_dict)
            
    result = {
        'messages': formatted_messages,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }
    
    return jsonify(result)


@bp.route('/<message_id>', methods=['GET'])
@db_session
def get_message(message_id: str, session: Session):
    """Get a single message by ID with its media."""
    if not validate_uuid(message_id):
        return error_response(400, "Invalid message ID format")
    
    # Get message with media
    message = session.query(Message).filter(Message.id == message_id) \
        .options(joinedload(Message.media_items)) \
        .first()
    
    if not message:
        return error_response(404, "Message not found")
    
    # Get referenced media
    referenced_media = []
    if message.meta_info and 'referenced_media' in message.meta_info:
        media_refs = message.meta_info['referenced_media']
        media_ids = [ref.get('id') for ref in media_refs if ref.get('id')]
        
        if media_ids:
            referenced_media = session.query(Media).filter(
                Media.id.in_(media_ids)
            ).all()
    
    # Create response
    result = MessageDetail.from_orm(message).dict()
    
    # Add media from media_items for compatibility
    if hasattr(message, 'media_items') and message.media_items:
        result['media'] = MediaBase.from_orm(message.media_items[0]).dict() if message.media_items else None
    result['media_items'] = [MediaBase.from_orm(media).dict() for media in message.media_items] if hasattr(message, 'media_items') else []
    
    # Add referenced media
    result['referenced_media'] = [
        MediaBase.from_orm(media).dict() for media in referenced_media
    ]
    
    # Get conversation title
    conversation = session.query(Conversation) \
        .filter(Conversation.id == message.conversation_id) \
        .first()
    
    if conversation:
        result['conversation_title'] = conversation.title
    
    return jsonify(result)


@bp.route('/<message_id>/context', methods=['GET'])
@db_session
def get_message_context(message_id: str, session: Session):
    """Get the context around a message (previous and next messages)."""
    if not validate_uuid(message_id):
        return error_response(400, "Invalid message ID format")
    
    # Get context size from request
    context_size = request.args.get('size', 5, type=int)
    
    # Ensure reasonable values
    context_size = max(1, min(20, context_size))
    
    # Get the message to find its conversation and timestamp
    message = session.query(Message).filter(Message.id == message_id).first()
    
    if not message:
        return error_response(404, "Message not found")
    
    # Get previous messages
    prev_messages = session.query(Message) \
        .filter(
            Message.conversation_id == message.conversation_id,
            Message.created_at < message.created_at
        ) \
        .order_by(desc(Message.created_at)) \
        .limit(context_size) \
        .all()
    
    # Get next messages
    next_messages = session.query(Message) \
        .filter(
            Message.conversation_id == message.conversation_id,
            Message.created_at > message.created_at
        ) \
        .order_by(Message.created_at) \
        .limit(context_size) \
        .all()
    
    # Format response
    result = {
        'message': MessageBase.from_orm(message).dict(),
        'previous_messages': [MessageBase.from_orm(msg).dict() for msg in reversed(prev_messages)],
        'next_messages': [MessageBase.from_orm(msg).dict() for msg in next_messages],
        'conversation_id': str(message.conversation_id)
    }
    
    return jsonify(result)