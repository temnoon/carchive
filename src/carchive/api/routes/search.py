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
        include_content = request.args.get('include_content', 'true').lower() == 'true'
    else:  # POST
        data = request.get_json() or {}
        query = data.get('query', '')
        embedding_model = data.get('model', 'default')
        limit = data.get('limit', 10)
        include_content = data.get('include_content', True)
    
    # Validate query
    if not query:
        return error_response(400, "Query parameter is required")
    
    try:
        # Import here to avoid circular imports
        from carchive.embeddings.embed import get_embedding
        from carchive.embeddings.embed_manager import EmbeddingManager
        
        # Generate embedding for the query
        embedding_vector = get_embedding(query, model_name=embedding_model)
        
        # Use the embedding manager to search
        embed_manager = EmbeddingManager()
        results = embed_manager.search_similar(embedding_vector, limit=limit)
        
        # Format response
        formatted_results = []
        for result in results:
            # Get the message associated with this embedding
            message = session.query(Message).filter(Message.id == result.parent_message_id).first()
            if message:
                message_data = MessageBase.from_orm(message).dict()
                if not include_content:
                    # Trim content to save bandwidth if not needed
                    message_data['content'] = message_data['content'][:100] + '...' if len(message_data['content']) > 100 else message_data['content']
                
                formatted_results.append({
                    'message': message_data,
                    'score': result.similarity_score,
                    'conversation_id': str(message.conversation_id),
                    'embedding_id': str(result.id)
                })
        
        return jsonify({
            'query': query,
            'model': embedding_model,
            'results': formatted_results
        })
        
    except ImportError:
        # Fallback to text search if embedding modules not available
        logger.warning("Embedding modules not available, falling back to text search")
        messages = session.query(Message).filter(
            Message.content.ilike(f'%{query}%')
        ).options(joinedload(Message.media)).order_by(desc(Message.created_at)).limit(limit).all()
        
        # Format response
        result = {
            'query': query,
            'model': embedding_model,
            'fallback': 'text_search',  # Indicate this is a fallback
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


@bp.route('/unified', methods=['GET', 'POST'])
@db_session
def unified_search(session: Session):
    """
    Unified search endpoint that combines text and vector search with advanced filtering.
    
    This endpoint provides a comprehensive interface to the search capabilities,
    allowing filtering by entity type, date range, sort order, and more.
    """
    # Determine if this is a GET or POST request and extract parameters accordingly
    if request.method == 'GET':
        # Extract query parameters
        query = request.args.get('q', '')
        entity_types = request.args.getlist('entity_type') or ['all']
        search_mode = request.args.get('mode', 'substring')
        sort_by = request.args.get('sort', 'relevance')
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        conversation_id = request.args.get('conversation_id')
        
        # Date filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        days = request.args.get('days', type=int)
        
        # Role and provider filters
        roles = request.args.getlist('role')
        providers = request.args.getlist('provider')
        
        # Advanced options
        gencom_types = request.args.getlist('gencom_type')
        include_content = request.args.get('include_content', 'true').lower() == 'true'
        
    else:  # POST request
        data = request.get_json() or {}
        query = data.get('query', '')
        entity_types = data.get('entity_types', ['all'])
        search_mode = data.get('mode', 'substring')
        sort_by = data.get('sort_by', 'relevance')
        limit = data.get('limit', 10)
        offset = data.get('offset', 0)
        conversation_id = data.get('conversation_id')
        
        # Date filters
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        days = data.get('days')
        
        # Role and provider filters
        roles = data.get('roles', [])
        providers = data.get('providers', [])
        
        # Advanced options
        gencom_types = data.get('gencom_types', [])
        include_content = data.get('include_content', True)
    
    # Convert entity types to consistent format
    entity_types = [et.lower() for et in entity_types]
    
    try:
        # Import here to avoid circular imports
        from carchive.search.unified.manager import SearchManager
        from carchive.search.unified.schemas import (
            SearchCriteria, SearchMode, EntityType, SortOrder, DateRange
        )
        
        # Convert string parameters to appropriate enum values
        try:
            search_mode_enum = SearchMode(search_mode.lower())
        except ValueError:
            search_mode_enum = SearchMode.SUBSTRING
            
        try:
            sort_by_enum = SortOrder(sort_by.lower())
        except ValueError:
            sort_by_enum = SortOrder.DATE_DESC
        
        # Convert entity types to enum values
        entity_type_enums = []
        for entity_type in entity_types:
            try:
                entity_type_enums.append(EntityType(entity_type.lower()))
            except ValueError:
                logger.warning(f"Unknown entity type: {entity_type}")
                continue
        
        if not entity_type_enums:
            entity_type_enums = [EntityType.ALL]
        
        # Create date range if applicable
        date_range = None
        if start_date or end_date or days:
            date_range = DateRange(
                start=start_date,
                end=end_date,
                days=days
            )
        
        # Create search criteria
        criteria = SearchCriteria(
            query=query,
            mode=search_mode_enum,
            entity_types=entity_type_enums,
            sort_by=sort_by_enum,
            limit=limit,
            offset=offset,
            date_range=date_range,
            roles=roles,
            providers=providers,
            conversation_id=conversation_id,
            gencom_types=gencom_types
        )
        
        # Execute the search
        search_manager = SearchManager()
        results = search_manager.search(criteria)
        
        # Format the results for API response
        formatted_results = []
        for result in results.results:
            result_dict = result.dict()
            
            # Format content based on include_content parameter
            if not include_content and 'content' in result_dict:
                result_dict['content'] = result_dict['content'][:100] + '...' if len(result_dict['content']) > 100 else result_dict['content']
            
            formatted_results.append(result_dict)
        
        response = {
            'query': query,
            'criteria': criteria.dict(),
            'total_count': results.total_count,
            'query_time_ms': results.query_time_ms,
            'results': formatted_results,
            'pagination': {
                'offset': offset,
                'limit': limit,
                'has_more': offset + limit < results.total_count
            }
        }
        
        return jsonify(response)
        
    except ImportError as e:
        logger.error(f"Error importing search modules: {e}")
        return error_response(500, f"Search functionality not available: {str(e)}")
    except Exception as e:
        logger.error(f"Error performing unified search: {e}")
        return error_response(500, f"Error performing search: {str(e)}")


@bp.route('/save', methods=['POST'])
@db_session
def save_search(session: Session):
    """Save a search query for future reference."""
    # Get parameters
    data = request.get_json() or {}
    
    query = data.get('query')
    name = data.get('name')
    search_type = data.get('type', 'all')
    criteria = data.get('criteria', {})
    
    # Validate required fields
    if not query:
        return error_response(400, "Query parameter is required")
    if not name:
        return error_response(400, "Name parameter is required")
    
    try:
        # Create a search criteria record in the database
        from datetime import datetime
        from uuid import uuid4
        from carchive.database.models import SavedSearch
        
        # Create a new saved search
        saved_search = SavedSearch(
            id=str(uuid4()),
            name=name,
            query=query,
            search_type=search_type,
            criteria=criteria,
            created_at=datetime.utcnow()
        )
        
        session.add(saved_search)
        session.commit()
        
        return jsonify({
            'success': True,
            'name': name,
            'query': query,
            'type': search_type,
            'id': saved_search.id,
            'created_at': saved_search.created_at.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error saving search: {e}")
        return error_response(500, f"Error saving search: {str(e)}")


@bp.route('/saved', methods=['GET'])
@db_session
def get_saved_searches(session: Session):
    """Retrieve saved searches."""
    # Get pagination parameters
    page, per_page = parse_pagination_params()
    
    try:
        from carchive.database.models import SavedSearch
        
        # Get saved searches with pagination
        query = session.query(SavedSearch).order_by(desc(SavedSearch.created_at))
        total = query.count()
        saved_searches = query.offset((page - 1) * per_page).limit(per_page).all()
        
        # Format response
        result = {
            'searches': [
                {
                    'id': str(ss.id),
                    'name': ss.name,
                    'query': ss.query,
                    'type': ss.search_type,
                    'criteria': ss.criteria,
                    'created_at': ss.created_at.isoformat() if ss.created_at else None,
                    'updated_at': ss.updated_at.isoformat() if ss.updated_at else None
                }
                for ss in saved_searches
            ],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error retrieving saved searches: {e}")
        return error_response(500, f"Error retrieving saved searches: {str(e)}")


@bp.route('/saved/<search_id>', methods=['GET'])
@db_session
def get_saved_search(session: Session, search_id: str):
    """Retrieve a specific saved search by ID."""
    try:
        from carchive.database.models import SavedSearch
        
        # Get the saved search
        saved_search = session.query(SavedSearch).filter(SavedSearch.id == search_id).first()
        
        if not saved_search:
            return error_response(404, f"Saved search with ID {search_id} not found")
        
        # Format response
        result = {
            'id': str(saved_search.id),
            'name': saved_search.name,
            'query': saved_search.query,
            'type': saved_search.search_type,
            'criteria': saved_search.criteria,
            'created_at': saved_search.created_at.isoformat() if saved_search.created_at else None,
            'updated_at': saved_search.updated_at.isoformat() if saved_search.updated_at else None
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error retrieving saved search: {e}")
        return error_response(500, f"Error retrieving saved search: {str(e)}")