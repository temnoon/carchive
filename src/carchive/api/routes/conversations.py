"""
API endpoints for conversations.
"""

from typing import Dict, List, Optional, Any
from uuid import UUID
from flask import Blueprint, request, jsonify, send_file, url_for
from sqlalchemy import desc, func, cast
from sqlalchemy.orm import joinedload, Session

from carchive.database.models import Conversation, Message, Media, MessageMedia
from carchive.api.schemas import ConversationBase, ConversationDetail, MessageDetail, MediaBase
from carchive.api.routes.utils import (
    db_session, validate_uuid, parse_pagination_params, 
    paginate_query, error_response
)

bp = Blueprint('conversations', __name__, url_prefix='/api/conversations')


@bp.route('/', methods=['GET'])
@db_session
def get_conversations(session: Session):
    """Get a list of conversations with pagination."""
    page, per_page = parse_pagination_params()
    
    # Get query filters
    title_filter = request.args.get('title')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = session.query(Conversation)
    
    # Apply filters
    if title_filter:
        query = query.filter(Conversation.title.ilike(f'%{title_filter}%'))
    if start_date:
        query = query.filter(Conversation.created_at >= start_date)
    if end_date:
        query = query.filter(Conversation.created_at <= end_date)
    
    # Apply sorting
    if sort_order.lower() == 'asc':
        query = query.order_by(getattr(Conversation, sort_by))
    else:
        query = query.order_by(desc(getattr(Conversation, sort_by)))
    
    # Get message counts
    message_counts = session.query(
        Message.conversation_id,
        func.count(Message.id).label('count')
    ).group_by(Message.conversation_id).all()
    message_count_dict = {str(cid): count for cid, count in message_counts}
    
    # Get media counts per conversation
    media_count_query = session.query(
        Message.conversation_id,
        func.count(MessageMedia.media_id.distinct()).label('media_count')
    ).join(
        MessageMedia, MessageMedia.message_id == Message.id
    ).group_by(
        Message.conversation_id
    ).all()
    media_count_dict = {str(cid): count for cid, count in media_count_query}
    
    # Paginate results
    conversations, total = paginate_query(query, page, per_page)
    
    # Format response
    result = {
        'conversations': [
            {
                **ConversationBase.from_orm(conv).dict(),
                'message_count': message_count_dict.get(str(conv.id), 0),
                'media_count': media_count_dict.get(str(conv.id), 0)
            }
            for conv in conversations
        ],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }
    
    return jsonify(result)


@bp.route('/<conversation_id>', methods=['GET'])
@db_session
def get_conversation(conversation_id: str, session: Session):
    """Get a single conversation by ID with its messages."""
    if not validate_uuid(conversation_id):
        return error_response(400, "Invalid conversation ID format")
    
    # Get include_messages parameter
    include_messages = request.args.get('include_messages', 'true').lower() == 'true'
    
    # Get conversation
    conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        return error_response(404, "Conversation not found")
    
    # Prepare response
    result = ConversationBase.from_orm(conversation).dict()
    
    # Include message count
    message_count = session.query(func.count(Message.id)).filter(
        Message.conversation_id == conversation.id
    ).scalar()
    result['message_count'] = message_count
    
    # Include media count
    media_count = session.query(func.count(MessageMedia.media_id.distinct())).join(
        Message, Message.id == MessageMedia.message_id
    ).filter(
        Message.conversation_id == conversation.id
    ).scalar()
    result['media_count'] = media_count
    
    # Include messages if requested
    if include_messages:
        # Get pagination parameters
        page, per_page = parse_pagination_params()
        
        # Query messages 
        query = session.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at)
        
        # Paginate messages
        messages, _ = paginate_query(query, page, per_page)
        
        # Get media for each message
        media_by_message = {}
        message_ids = [msg.id for msg in messages]
        
        if message_ids:
            # Query media items associated with these messages
            media_query = session.query(Media).join(
                MessageMedia, MessageMedia.media_id == Media.id
            ).filter(
                MessageMedia.message_id.in_(message_ids)
            ).all()
            
            # Group media by message_id
            for media in media_query:
                for assoc in media.message_associations:
                    if str(assoc.message_id) in [str(mid) for mid in message_ids]:
                        if str(assoc.message_id) not in media_by_message:
                            media_by_message[str(assoc.message_id)] = []
                        media_by_message[str(assoc.message_id)].append(media)
        
        # Format messages with their media items
        result['messages'] = [
            {
                **MessageDetail.from_orm(msg).dict(),
                'media_items': [
                    {
                        'id': str(media.id),
                        'file_path': media.file_path,
                        'media_type': media.media_type,
                        'created_at': media.created_at.isoformat() if media.created_at else None,
                        'file_name': media.file_name,
                        'original_file_id': media.original_file_id,
                        'is_generated': media.is_generated
                    } for media in media_by_message.get(str(msg.id), [])
                ]
            }
            for msg in messages
        ]
        
        # Add pagination info for messages
        result['pagination'] = {
            'page': page,
            'per_page': per_page,
            'total': message_count,
            'pages': (message_count + per_page - 1) // per_page
        }
    
    return jsonify(result)


@bp.route('/<conversation_id>/summary', methods=['GET'])
@db_session
def get_conversation_summary(conversation_id: str, session: Session):
    """Get a summary of a conversation."""
    if not validate_uuid(conversation_id):
        return error_response(400, "Invalid conversation ID format")
    
    # Get conversation
    conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    if not conversation:
        return error_response(404, "Conversation not found")
    
    # Get summary from meta_info if available
    summary = None
    if conversation.meta_info and 'summary' in conversation.meta_info:
        summary = conversation.meta_info['summary']
    
    # If no summary, check if there's an agent output with a summary
    if not summary:
        # TODO: Add code to retrieve summary from AgentOutput if available
        pass
    
    return jsonify({
        'conversation_id': str(conversation.id),
        'title': conversation.title,
        'summary': summary or "No summary available"
    })
