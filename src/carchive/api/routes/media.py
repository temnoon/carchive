"""
API endpoints for media files.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, send_file, current_app, abort
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload, Session
from werkzeug.utils import secure_filename

from carchive.database.models import Media, Message
from carchive.api.schemas import MediaBase, MediaDetail
from carchive.api.routes.utils import (
    db_session, validate_uuid, parse_pagination_params, 
    paginate_query, error_response
)

bp = Blueprint('media', __name__, url_prefix='/api/media')


@bp.route('/', methods=['GET'])
@db_session
def get_media_files(session: Session):
    """Get a list of media files with pagination."""
    page, per_page = parse_pagination_params()
    
    # Get query filters
    media_type = request.args.get('type')
    is_generated = request.args.get('is_generated', '').lower()
    file_id = request.args.get('file_id')
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    # Build query
    query = session.query(Media)
    
    # Apply filters
    if media_type:
        query = query.filter(Media.media_type == media_type)
    
    if is_generated == 'true':
        query = query.filter(Media.is_generated == True)
    elif is_generated == 'false':
        query = query.filter(Media.is_generated == False)
    
    if file_id:
        query = query.filter(Media.original_file_id == file_id)
    
    # Apply sorting
    if sort_order.lower() == 'asc':
        query = query.order_by(getattr(Media, sort_by))
    else:
        query = query.order_by(desc(getattr(Media, sort_by)))
    
    # Paginate results
    media_files, total = paginate_query(query, page, per_page)
    
    # Format response
    result = {
        'media': [MediaBase.from_orm(media).dict() for media in media_files],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    }
    
    return jsonify(result)


@bp.route('/<media_id>', methods=['GET'])
@db_session
def get_media(media_id: str, session: Session):
    """Get a single media file by ID with its message associations."""
    if not validate_uuid(media_id):
        return error_response(400, "Invalid media ID format")
    
    # Get media with related messages
    media = session.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        return error_response(404, "Media not found")
    
    # Get uploader message
    uploader_message = None
    if media.message_id:
        uploader_message = session.query(Message).filter(
            Message.id == media.message_id
        ).first()
    
    # Get linked message
    linked_message = None
    if hasattr(media, 'linked_message_id') and media.linked_message_id:
        linked_message = session.query(Message).filter(
            Message.id == media.linked_message_id
        ).first()
    
    # Create response
    result = MediaBase.from_orm(media).dict()
    
    # Add message info
    if uploader_message:
        result['uploader_message'] = {
            'id': str(uploader_message.id),
            'content': uploader_message.content[:200] + '...' if uploader_message.content and len(uploader_message.content) > 200 else uploader_message.content,
            'created_at': uploader_message.created_at,
            'conversation_id': str(uploader_message.conversation_id)
        }
    
    if linked_message:
        result['linked_message'] = {
            'id': str(linked_message.id),
            'content': linked_message.content[:200] + '...' if linked_message.content and len(linked_message.content) > 200 else linked_message.content,
            'created_at': linked_message.created_at,
            'conversation_id': str(linked_message.conversation_id)
        }
    
    return jsonify(result)


@bp.route('/<media_id>/file', methods=['GET'])
@db_session
def get_media_file(media_id: str, session: Session):
    """Serve the actual media file."""
    if not validate_uuid(media_id):
        return error_response(400, "Invalid media ID format")
    
    # Get media
    media = session.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        return error_response(404, "Media not found")
    
    # Get file path
    file_path = media.file_path
    
    # Check if file exists
    if not os.path.isfile(file_path):
        return error_response(404, "Media file not found on disk")
    
    # Determine content type
    content_type = None
    if media.media_type == 'image':
        if file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            content_type = 'image/png'
        elif file_path.lower().endswith('.gif'):
            content_type = 'image/gif'
        elif file_path.lower().endswith('.webp'):
            content_type = 'image/webp'
        else:
            content_type = 'image/jpeg'  # default
    elif media.media_type == 'audio':
        if file_path.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif file_path.lower().endswith('.wav'):
            content_type = 'audio/wav'
        else:
            content_type = 'audio/mpeg'  # default
    elif media.media_type == 'pdf':
        content_type = 'application/pdf'
    
    # Serve file
    return send_file(file_path, mimetype=content_type)


@bp.route('/types', methods=['GET'])
@db_session
def get_media_types(session: Session):
    """Get a list of all media types and their counts."""
    # Get counts by media type
    counts = session.query(
        Media.media_type, 
        func.count(Media.id).label('count')
    ).group_by(Media.media_type).all()
    
    # Format response
    result = {
        'types': [
            {'type': media_type, 'count': count}
            for media_type, count in counts
        ],
        'total': sum(count for _, count in counts)
    }
    
    return jsonify(result)