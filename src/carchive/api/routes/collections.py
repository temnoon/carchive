"""
API endpoints for collection management.
"""

from typing import Dict, List, Optional, Any, Union
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, func, or_, cast, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload, Session
import json
from uuid import UUID, uuid4
from datetime import datetime

from carchive.database.models import Collection, CollectionItem, Message, Conversation, Chunk
from carchive.api.schemas import (
    CollectionBase, CollectionCreate, CollectionUpdate, 
    CollectionDetail, CollectionItemBase
)
from carchive.api.routes.utils import (
    db_session, parse_pagination_params, error_response
)
from carchive.collections.collection_manager import CollectionManager
from carchive.collections.schemas import CollectionItemSchema

bp = Blueprint('collections', __name__, url_prefix='/api/collections')


@bp.route('/', methods=['GET'])
@db_session
def list_collections(session: Session):
    """List all collections with pagination."""
    # Get pagination parameters
    page, per_page = parse_pagination_params()
    
    try:
        # Query collections with pagination
        query = session.query(Collection).order_by(desc(Collection.created_at))
        total = query.count()
        collections = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Count items in each collection
        collection_data = []
        for coll in collections:
            item_count = session.query(func.count(CollectionItem.id)).filter_by(collection_id=coll.id).scalar() or 0
            coll_dict = CollectionBase.from_orm(coll).dict()
            coll_dict['item_count'] = item_count
            collection_data.append(coll_dict)
        
        # Format response
        result = {
            'collections': collection_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving collections: {e}")
        return error_response(500, f"Error retrieving collections: {str(e)}")


@bp.route('/<collection_id>', methods=['GET'])
@db_session
def get_collection(session: Session, collection_id: str):
    """Get a specific collection by ID."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
        except ValueError:
            return error_response(400, "Invalid collection ID format")
        
        # Get the collection
        collection = session.query(Collection).filter_by(id=collection_uuid).first()
        
        if not collection:
            return error_response(404, f"Collection with ID {collection_id} not found")
        
        # Get collection items
        items = session.query(CollectionItem).filter_by(collection_id=collection_uuid).all()
        
        # Format collection items with associated entity details
        formatted_items = []
        for item in items:
            item_data = {
                'id': str(item.id),
                'meta_info': item.meta_info,
                'entity_type': None,
                'entity': None
            }
            
            # Determine entity type and fetch details
            if item.message_id:
                item_data['entity_type'] = 'message'
                message = session.query(Message).filter_by(id=item.message_id).first()
                if message:
                    item_data['entity'] = {
                        'id': str(message.id),
                        'content': message.content[:200] + "..." if message.content and len(message.content) > 200 else message.content,
                        'conversation_id': str(message.conversation_id),
                        'created_at': message.created_at.isoformat() if message.created_at else None
                    }
            elif item.conversation_id:
                item_data['entity_type'] = 'conversation'
                conversation = session.query(Conversation).filter_by(id=item.conversation_id).first()
                if conversation:
                    item_data['entity'] = {
                        'id': str(conversation.id),
                        'title': conversation.title,
                        'created_at': conversation.created_at.isoformat() if conversation.created_at else None
                    }
            elif item.chunk_id:
                item_data['entity_type'] = 'chunk'
                chunk = session.query(Chunk).filter_by(id=item.chunk_id).first()
                if chunk:
                    item_data['entity'] = {
                        'id': str(chunk.id),
                        'content': chunk.content[:200] + "..." if chunk.content and len(chunk.content) > 200 else chunk.content,
                        'message_id': str(chunk.message_id) if chunk.message_id else None,
                        'created_at': chunk.created_at.isoformat() if chunk.created_at else None
                    }
            
            formatted_items.append(item_data)
        
        # Format response
        result = {
            'id': str(collection.id),
            'name': collection.name,
            'created_at': collection.created_at.isoformat() if collection.created_at else None,
            'meta_info': collection.meta_info,
            'items': formatted_items,
            'item_count': len(formatted_items)
        }
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving collection: {e}")
        return error_response(500, f"Error retrieving collection: {str(e)}")


@bp.route('/', methods=['POST'])
@db_session
def create_collection(session: Session):
    """Create a new collection."""
    try:
        # Get request data
        data = request.get_json() or {}
        
        # Validate required fields
        if 'name' not in data:
            return error_response(400, "Name is required")
        
        # Create collection schema
        items = []
        if 'items' in data and data['items']:
            for item in data['items']:
                # Convert dict to CollectionItemSchema
                item_schema = CollectionItemSchema(
                    message_id=item.get('message_id'),
                    conversation_id=item.get('conversation_id'),
                    chunk_id=item.get('chunk_id'),
                    meta_info=item.get('meta_info')
                )
                items.append(item_schema)
        
        collection_data = {
            'name': data['name'],
            'meta_info': data.get('meta_info'),
            'items': items
        }
        
        # Create collection
        from carchive.collections.schemas import CollectionCreateSchema
        collection_schema = CollectionCreateSchema(**collection_data)
        collection = CollectionManager.create_collection(collection_schema)
        
        # Format response
        result = {
            'id': str(collection.id),
            'name': collection.name,
            'created_at': collection.created_at.isoformat() if collection.created_at else None,
            'meta_info': collection.meta_info,
            'item_count': len(items)
        }
        
        return jsonify(result), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating collection: {e}")
        return error_response(500, f"Error creating collection: {str(e)}")


@bp.route('/<collection_id>', methods=['PUT'])
@db_session
def update_collection(session: Session, collection_id: str):
    """Update an existing collection."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
        except ValueError:
            return error_response(400, "Invalid collection ID format")
        
        # Get request data
        data = request.get_json() or {}
        
        # Create update schema
        from carchive.collections.schemas import CollectionUpdateSchema
        update_data = CollectionUpdateSchema(
            name=data.get('name'),
            meta_info=data.get('meta_info')
        )
        
        # Update collection
        collection = CollectionManager.update_collection(collection_id, update_data)
        
        # Format response
        result = {
            'id': str(collection.id),
            'name': collection.name,
            'created_at': collection.created_at.isoformat() if collection.created_at else None,
            'meta_info': collection.meta_info,
            'updated': True
        }
        
        return jsonify(result)
        
    except ValueError as e:
        current_app.logger.error(f"Error updating collection: {e}")
        return error_response(404, str(e))
        
    except Exception as e:
        current_app.logger.error(f"Error updating collection: {e}")
        return error_response(500, f"Error updating collection: {str(e)}")


@bp.route('/<collection_id>', methods=['DELETE'])
@db_session
def delete_collection(session: Session, collection_id: str):
    """Delete a collection."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
        except ValueError:
            return error_response(400, "Invalid collection ID format")
        
        # Delete collection
        result = CollectionManager.delete_collection(collection_id)
        
        # Format response
        return jsonify({
            'id': collection_id,
            'deleted': result
        })
        
    except ValueError as e:
        current_app.logger.error(f"Error deleting collection: {e}")
        return error_response(404, str(e))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting collection: {e}")
        return error_response(500, f"Error deleting collection: {str(e)}")


@bp.route('/<collection_id>/items', methods=['POST'])
@db_session
def add_collection_items(session: Session, collection_id: str):
    """Add items to a collection."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
        except ValueError:
            return error_response(400, "Invalid collection ID format")
        
        # Get request data
        data = request.get_json() or {}
        
        if 'items' not in data or not data['items']:
            return error_response(400, "Items are required")
        
        # Convert items to schema objects
        items = []
        for item in data['items']:
            item_schema = CollectionItemSchema(
                message_id=item.get('message_id'),
                conversation_id=item.get('conversation_id'),
                chunk_id=item.get('chunk_id'),
                meta_info=item.get('meta_info')
            )
            items.append(item_schema)
        
        # Add items to collection
        result = CollectionManager.add_items(collection_id, items)
        
        # Format response
        return jsonify({
            'collection_id': collection_id,
            'items_added': len(items),
            'success': result
        })
        
    except ValueError as e:
        current_app.logger.error(f"Error adding items to collection: {e}")
        return error_response(404, str(e))
        
    except Exception as e:
        current_app.logger.error(f"Error adding items to collection: {e}")
        return error_response(500, f"Error adding items to collection: {str(e)}")


@bp.route('/<collection_id>/items/<item_id>', methods=['DELETE'])
@db_session
def remove_collection_item(session: Session, collection_id: str, item_id: str):
    """Remove an item from a collection."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
            item_uuid = UUID(item_id)
        except ValueError:
            return error_response(400, "Invalid ID format")
        
        # Remove item from collection
        result = CollectionManager.remove_item(collection_id, item_id)
        
        # Format response
        return jsonify({
            'collection_id': collection_id,
            'item_id': item_id,
            'deleted': result
        })
        
    except ValueError as e:
        current_app.logger.error(f"Error removing item from collection: {e}")
        return error_response(404, str(e))
        
    except Exception as e:
        current_app.logger.error(f"Error removing item from collection: {e}")
        return error_response(500, f"Error removing item from collection: {str(e)}")


@bp.route('/<collection_id>/render', methods=['GET'])
@db_session
def render_collection(session: Session, collection_id: str):
    """Render a collection as HTML (basic version for API)."""
    try:
        # Validate UUID format
        try:
            collection_uuid = UUID(collection_id)
        except ValueError:
            return error_response(400, "Invalid collection ID format")
        
        # Get collection
        collection = session.query(Collection).filter_by(id=collection_uuid).first()
        
        if not collection:
            return error_response(404, f"Collection with ID {collection_id} not found")
        
        # Import render function
        from carchive.collections.render_engine import render_collection_to_html
        from tempfile import NamedTemporaryFile
        import os
        
        # Create temporary file
        with NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Render collection to HTML
            render_collection_to_html(
                collection.name,
                temp_path,
                include_conversation_info=True,
                include_message_metadata=False
            )
            
            # Read HTML content
            with open(temp_path, 'r') as f:
                html_content = f.read()
            
            # Return HTML
            return html_content, 200, {'Content-Type': 'text/html'}
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        
    except Exception as e:
        current_app.logger.error(f"Error rendering collection: {e}")
        return error_response(500, f"Error rendering collection: {str(e)}")