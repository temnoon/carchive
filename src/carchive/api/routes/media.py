"""
API endpoints for media files.
"""

import os
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask import Blueprint, request, jsonify, send_file, current_app, abort, redirect, url_for
from sqlalchemy import desc, func
from sqlalchemy.orm import joinedload, Session
from werkzeug.utils import secure_filename
from flask_cors import cross_origin

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
    logger = logging.getLogger(__name__)
    
    try:
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
        try:
            result = MediaBase.from_orm(media).dict()
        except Exception as e:
            logger.error(f"Error converting media to dict: {str(e)}")
            # Fallback to manual serialization
            result = {
                'id': str(media.id),
                'original_file_name': media.original_file_name,
                'file_path': media.file_path,
                'media_type': media.media_type,
                'mime_type': getattr(media, 'mime_type', None),
                'is_generated': getattr(media, 'is_generated', False),
                'original_file_id': getattr(media, 'original_file_id', None),
                'file_size': getattr(media, 'file_size', None),
                'created_at': media.created_at.isoformat() if hasattr(media, 'created_at') and media.created_at else None
            }
        
        # Add message info - with proper datetime serialization
        if uploader_message:
            result['uploader_message'] = {
                'id': str(uploader_message.id),
                'content': uploader_message.content[:200] + '...' if uploader_message.content and len(uploader_message.content) > 200 else uploader_message.content,
                'created_at': uploader_message.created_at.isoformat() if hasattr(uploader_message, 'created_at') and uploader_message.created_at else None,
                'conversation_id': str(uploader_message.conversation_id)
            }
        
        if linked_message:
            result['linked_message'] = {
                'id': str(linked_message.id),
                'content': linked_message.content[:200] + '...' if linked_message.content and len(linked_message.content) > 200 else linked_message.content,
                'created_at': linked_message.created_at.isoformat() if hasattr(linked_message, 'created_at') and linked_message.created_at else None,
                'conversation_id': str(linked_message.conversation_id)
            }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Error getting media {media_id}: {str(e)}")
        logger.error(error_trace)
        return error_response(500, f"Error retrieving media: {str(e)}")


@bp.route('/<media_id>/file', methods=['GET'])
@cross_origin()
@db_session
def get_media_file(media_id: str, session: Session):
    """Serve the actual media file."""
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Accessing media ID: {media_id}")
        
        if not validate_uuid(media_id):
            return error_response(400, "Invalid media ID format")
        
        # Get media
        media = session.query(Media).filter(Media.id == media_id).first()
        
        if not media:
            return error_response(404, "Media not found")
        
        logger.info(f"Found media: {media.id}, original path: {media.file_path}")
        
        # Get file path
        file_path = media.file_path
        
        # Get media_dir from config (with fallback)
        from carchive.core.config import MEDIA_DIR
        media_dir = MEDIA_DIR or "media"
        
        # Enhanced list of possible paths to try
        possible_paths = [
            file_path,                                                    # Original path
            file_path.replace('chatgpt/', ''),                            # Without chatgpt/ prefix
            os.path.join(media_dir, os.path.basename(file_path)),         # In media/ root
            os.path.join(f"{media_dir}/chatgpt", os.path.basename(file_path)),  # In media/chatgpt
            # Additional fallback options
            os.path.join(".", file_path),                                 # Relative to current directory
            os.path.join("media", os.path.basename(file_path)),           # Hardcoded media dir
            os.path.join("../media", os.path.basename(file_path)),        # Up one level
        ]
        
        # Try the dall-e generations directory if this is a webp file (DALL-E images)
        if file_path.lower().endswith('.webp') or (media.original_file_id and 'dalle' in media.original_file_id.lower()):
            dalle_paths = [
                os.path.join('chat2/dalle-generations', os.path.basename(file_path)),
                os.path.join(media_dir, 'dalle-generations', os.path.basename(file_path)),
                os.path.join('media/dalle-generations', os.path.basename(file_path))
            ]
            possible_paths.extend(dalle_paths)
            
            # Also try with original file ID if available
            if media.original_file_id:
                dalle_id_paths = [
                    os.path.join('chat2/dalle-generations', f"{media.original_file_id}.webp"),
                    os.path.join(media_dir, 'dalle-generations', f"{media.original_file_id}.webp"),
                    os.path.join('media/dalle-generations', f"{media.original_file_id}.webp")
                ]
                possible_paths.extend(dalle_id_paths)
        
        # Try each path
        found = False
        for test_path in possible_paths:
            logger.info(f"Trying path: {test_path}")
            if os.path.isfile(test_path):
                file_path = test_path
                found = True
                logger.info(f"Found at: {file_path}")
                break
                
        if not found:
            logger.error(f"All attempts to find file failed. Tried: {possible_paths}")
            return error_response(404, f"Media file not found on disk. Tried {len(possible_paths)} possible paths.")
        
        # Determine content type based on file extension
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
        
        # Set default content type if still not determined
        if not content_type:
            content_type = 'application/octet-stream'
            
        logger.info(f"Serving file: {file_path} with content type: {content_type}")
        
        # Serve file with absolute path
        absolute_path = os.path.abspath(file_path)
        
        # Store correct path for future use if it differs from original
        if media.file_path != file_path:
            logger.info(f"Updating media record with correct path: {file_path}")
            media.file_path = file_path
            session.commit()
        
        try:
            # First check if file exists and is readable
            if not os.path.exists(absolute_path):
                logger.error(f"File does not exist: {absolute_path}")
                return error_response(404, f"File not found at {absolute_path}")
                
            if not os.access(absolute_path, os.R_OK):
                logger.error(f"File is not readable: {absolute_path}")
                return error_response(403, f"File not readable: {absolute_path}")
            
            # Open file to confirm it's accessible
            with open(absolute_path, "rb") as f:
                file_size = os.path.getsize(absolute_path)
                logger.info(f"File opened successfully: {absolute_path}, size: {file_size} bytes")
            
            # Use direct file serving with explicit content type
            response = send_file(
                absolute_path, 
                mimetype=content_type,
                as_attachment=False,
                download_name=os.path.basename(file_path)
            )
            
            # Add CORS headers explicitly
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            
            # Add cache control headers to improve performance
            response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache for 24 hours
            response.headers['Expires'] = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            return response
            
        except FileNotFoundError as fnf:
            logger.error(f"File not found error: {fnf}")
            return error_response(404, f"File not found: {absolute_path}")
        except PermissionError as pe:
            logger.error(f"Permission error: {pe}")
            return error_response(403, f"Permission denied: {absolute_path}")
        except Exception as se:
            logger.error(f"Error serving file: {se}")
            return error_response(500, f"Error serving file: {str(se)}")
        
    except Exception as e:
        # Log the full error
        import traceback
        logger.error(f"Error serving media file: {str(e)}")
        logger.error(traceback.format_exc())
        return error_response(500, f"Server error: {str(e)}")


@bp.route('/<media_id>/thumbnail', methods=['GET'])
@cross_origin()
@db_session
def get_media_thumbnail(media_id: str, session: Session):
    """Serve a thumbnail version of the media file.
    Currently just redirects to the original file, but could be enhanced with actual thumbnail generation.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Accessing thumbnail for media ID: {media_id}")
    
    if not validate_uuid(media_id):
        return error_response(400, "Invalid media ID format")
    
    # Get media
    media = session.query(Media).filter(Media.id == media_id).first()
    
    if not media:
        return error_response(404, "Media not found")
        
    # Only handle thumbnails for images
    if media.media_type != 'image':
        # For non-images, just redirect to the original file
        return redirect(url_for('media.get_media_file', media_id=media_id))
    
    # For now, just redirect to the original file
    # This placeholder can be enhanced later with actual thumbnail generation
    return redirect(url_for('media.get_media_file', media_id=media_id))


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


@bp.route('/<media_id>/file/debug', methods=['GET'])
@db_session
def debug_file_path(media_id: str, session: Session):
    """Debug endpoint to show file path resolution."""
    logger = logging.getLogger(__name__)
    logger.info(f"DEBUG: Checking file path resolution for media ID: {media_id}")
    
    if not validate_uuid(media_id):
        return jsonify({'error': 'Invalid UUID format'})
    
    # Get media record
    media = session.query(Media).filter(Media.id == media_id).first()
    if not media:
        return jsonify({'error': 'Media not found'})
    
    # Original file path
    file_path = media.file_path
    original_path = file_path
    
    # Get media_dir from config (with fallback)
    from carchive.core.config import MEDIA_DIR
    media_dir = MEDIA_DIR or "media"
    
    # List of possible paths to try
    possible_paths = [
        file_path,                                                    # Original path
        file_path.replace('chatgpt/', ''),                            # Without chatgpt/ prefix
        os.path.join(media_dir, os.path.basename(file_path)),         # In media/ root
        os.path.join(f"{media_dir}/chatgpt", os.path.basename(file_path)),  # In media/chatgpt
        # Additional fallback options
        os.path.join(".", file_path),                                 # Relative to current directory
        os.path.join("media", os.path.basename(file_path)),           # Hardcoded media dir
        os.path.join("../media", os.path.basename(file_path)),        # Up one level
    ]
    
    # Try the dall-e generations directory if this is a webp file (DALL-E images)
    if file_path.lower().endswith('.webp') or (media.original_file_id and 'dalle' in media.original_file_id.lower()):
        dalle_paths = [
            os.path.join('chat2/dalle-generations', os.path.basename(file_path)),
            os.path.join(media_dir, 'dalle-generations', os.path.basename(file_path)),
            os.path.join('media/dalle-generations', os.path.basename(file_path))
        ]
        possible_paths.extend(dalle_paths)
        
        # Also try with original file ID if available
        if media.original_file_id:
            dalle_id_paths = [
                os.path.join('chat2/dalle-generations', f"{media.original_file_id}.webp"),
                os.path.join(media_dir, 'dalle-generations', f"{media.original_file_id}.webp"),
                os.path.join('media/dalle-generations', f"{media.original_file_id}.webp")
            ]
            possible_paths.extend(dalle_id_paths)
    
    # Results for each path
    results = []
    for test_path in possible_paths:
        abs_path = os.path.abspath(test_path)
        result = {
            'path': test_path,
            'absolute_path': abs_path,
            'exists': os.path.isfile(abs_path),
            'readable': os.access(abs_path, os.R_OK) if os.path.isfile(abs_path) else False,
            'size': os.path.getsize(abs_path) if os.path.isfile(abs_path) else None
        }
        results.append(result)
    
    # Find the first working path
    working_path = None
    for result in results:
        if result['exists'] and result['readable']:
            working_path = result['path']
            break
    
    return jsonify({
        'media_id': media_id,
        'media_type': media.media_type,
        'original_path': original_path,
        'original_file_id': media.original_file_id if hasattr(media, 'original_file_id') else None,
        'working_path': working_path,
        'path_tests': results
    })


@bp.route('/schema', methods=['GET'])
@db_session
def media_schema(session: Session):
    """Return information about the Media table schema."""
    try:
        # Get one media record
        media = session.query(Media).first()
        
        if not media:
            return jsonify({'error': 'No media records found'})
        
        # Get all attributes
        attributes = dir(media)
        
        # Filter out private/system attributes
        public_attrs = [attr for attr in attributes if not attr.startswith('_')]
        
        # Get sample values
        values = {}
        for attr in public_attrs:
            try:
                value = getattr(media, attr)
                # Convert non-serializable types to strings
                if hasattr(value, '__dict__'):
                    value = str(value)
                values[attr] = value
            except Exception as e:
                values[attr] = f"ERROR: Could not access value - {str(e)}"
        
        return jsonify({
            'table': 'Media',
            'attributes': public_attrs,
            'sample_values': values
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@bp.route('/repair', methods=['GET', 'POST'])
@db_session
def repair_paths(session: Session):
    """Utility to check and repair media file paths."""
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        # Get all media with missing files
        missing_files = []
        repaired = []
        errors = []
        
        try:
            media_items = session.query(Media).all()
            logger.info(f"Checking {len(media_items)} media items for path repairs")
            
            for media in media_items:
                try:
                    if not os.path.exists(media.file_path):
                        # This file is missing at its recorded path
                        missing_files.append(str(media.id))
                        
                        # Try alternative paths
                        basename = os.path.basename(media.file_path)
                        
                        # Get media_dir from config (with fallback)
                        from carchive.core.config import MEDIA_DIR
                        media_dir = MEDIA_DIR or "media"
                        
                        # List of possible locations
                        alt_paths = [
                            media.file_path.replace('chatgpt/', ''),
                            os.path.join(media_dir, basename),
                            os.path.join('media/chatgpt', basename),
                            os.path.join('media', basename),
                            os.path.join('chat2/dalle-generations', basename)
                        ]
                        
                        # If we have an original ID, try that too
                        if hasattr(media, 'original_file_id') and media.original_file_id:
                            alt_paths.append(os.path.join('chat2/dalle-generations', f"{media.original_file_id}.webp"))
                        
                        # Check each path
                        found = False
                        for path in alt_paths:
                            if os.path.exists(path):
                                # Found it! Update the database
                                old_path = media.file_path
                                media.file_path = path
                                repaired.append({
                                    'id': str(media.id),
                                    'old_path': old_path,
                                    'new_path': path
                                })
                                found = True
                                break
                except Exception as item_error:
                    logger.error(f"Error checking media item {getattr(media, 'id', 'unknown')}: {str(item_error)}")
                    errors.append({
                        'id': str(getattr(media, 'id', 'unknown')),
                        'error': str(item_error)
                    })
            
            # Commit changes
            if repaired:
                session.commit()
                logger.info(f"Repaired {len(repaired)} media items")
            
            return jsonify({
                'total_checked': len(media_items),
                'missing_files': len(missing_files),
                'repaired': len(repaired),
                'errors': len(errors),
                'repaired_items': repaired,
                'error_items': errors
            })
            
        except Exception as e:
            import traceback
            logger.error(f"Error in repair_paths: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error',
                'message': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    # GET request - show repair form - return statistics
    try:
        total_count = session.query(func.count(Media.id)).scalar()
        missing_count = 0
        sample_missing = []
        
        # Check a sample of records for missing files
        sample_size = min(100, total_count)  # Check up to 100 records
        sample_records = session.query(Media).limit(sample_size).all()
        
        for media in sample_records:
            if not os.path.exists(media.file_path):
                missing_count += 1
                if len(sample_missing) < 10:  # Show up to 10 examples
                    sample_missing.append({
                        'id': str(media.id),
                        'path': media.file_path,
                        'name': media.original_file_name
                    })
        
        # Extrapolate to full database if needed
        estimated_missing = missing_count
        if sample_size < total_count:
            estimated_missing = int((missing_count / sample_size) * total_count)
        
        return jsonify({
            'status': 'ready',
            'total_media_items': total_count,
            'sample_size': sample_size,
            'missing_in_sample': missing_count,
            'estimated_missing_total': estimated_missing,
            'sample_missing_files': sample_missing,
            'instructions': 'POST to this endpoint to run the repair process'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500