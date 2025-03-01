"""
Conversation service module for conversation management operations.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Union

from sqlalchemy import desc, asc, func, and_, select
from sqlalchemy.orm import Session, joinedload, aliased

from carchive.database.models import Conversation, Message
from carchive.database.session import get_session
from carchive.schemas.db_objects import ConversationRead, MessageRead
from carchive.core.conversation_utils import export_conversation_to_json

def list_conversations(
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    filter_text: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    use_original_dates: bool = True,
    filter_by_date_field: str = "created_at",
) -> Tuple[List[ConversationRead], int]:
    """
    List conversations with optional filtering and sorting.
    
    Args:
        sort_by: Field to sort by (created_at, title, original_create_time, original_update_time)
        sort_order: Sort direction (asc, desc)
        limit: Maximum number of conversations to return
        offset: Number of conversations to skip
        filter_text: Optional text to filter by title
        start_date: Optional start date filter
        end_date: Optional end date filter
        use_original_dates: Use original dates from meta_info when available
        filter_by_date_field: Which date field to filter by (created_at, original_create_time, original_update_time)
        
    Returns:
        Tuple of (list of ConversationRead objects, total count)
    """
    with get_session() as session:
        query = session.query(Conversation)
        
        # Apply title filter
        if filter_text:
            query = query.filter(Conversation.title.ilike(f"%{filter_text}%"))
        
        # Apply date filters
        # For original dates, we need to post-filter after fetching
        if start_date or end_date:
            if filter_by_date_field == "created_at" or not use_original_dates:
                if start_date:
                    query = query.filter(Conversation.created_at >= start_date)
                if end_date:
                    query = query.filter(Conversation.created_at <= end_date)
            elif filter_by_date_field in ["original_create_time", "original_update_time"]:
                # For original date fields, we'll filter after fetching from DB
                # JSON queries could be used here, but would require database-specific syntax
                pass
        
        # Get total count (approximation before post-filtering)
        total_count = query.count()
        
        # Apply sorting for standard fields
        if sort_by == "title":
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Conversation.title))
            else:
                query = query.order_by(desc(Conversation.title))
        elif sort_by in ["original_create_time", "original_update_time"] and use_original_dates:
            # We'll need to sort post-query for fields in meta_info
            # First fetch ordered by DB create date as a fallback
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Conversation.created_at))
            else:
                query = query.order_by(desc(Conversation.created_at))
        else:
            # Default to created_at
            if sort_order.lower() == "asc":
                query = query.order_by(asc(Conversation.created_at))
            else:
                query = query.order_by(desc(Conversation.created_at))
        
        # Get conversations without pagination yet
        all_conversations = [ConversationRead.from_orm(c) for c in query.all()]
        
        # Get first and last message timestamps for all conversations
        if use_original_dates:
            conversation_ids = [c.id for c in all_conversations]
            if conversation_ids:
                # Get first message time for each conversation
                first_message_query = (
                    session.query(
                        Message.conversation_id,
                        func.min(Message.created_at).label('first_message_time')
                    )
                    .filter(Message.conversation_id.in_(conversation_ids))
                    .group_by(Message.conversation_id)
                )
                first_message_times = {
                    str(cid): time for cid, time in first_message_query.all()
                }
                
                # Get last message time for each conversation
                last_message_query = (
                    session.query(
                        Message.conversation_id,
                        func.max(Message.created_at).label('last_message_time')
                    )
                    .filter(Message.conversation_id.in_(conversation_ids))
                    .group_by(Message.conversation_id)
                )
                last_message_times = {
                    str(cid): time for cid, time in last_message_query.all()
                }
                
                # Inject message timestamps into conversation objects
                for conversation in all_conversations:
                    conv_id = str(conversation.id)
                    if conv_id in first_message_times:
                        conversation._first_message_time = first_message_times[conv_id]
                    if conv_id in last_message_times:
                        conversation._last_message_time = last_message_times[conv_id]
        
        # Post-filter and sort based on original dates if needed
        if use_original_dates:
            if filter_by_date_field == "original_create_time":
                if start_date:
                    all_conversations = [c for c in all_conversations 
                                     if c.original_create_time and c.original_create_time >= start_date]
                if end_date:
                    all_conversations = [c for c in all_conversations 
                                     if c.original_create_time and c.original_create_time <= end_date]
            elif filter_by_date_field == "original_update_time":
                if start_date:
                    all_conversations = [c for c in all_conversations 
                                     if c.original_update_time and c.original_update_time >= start_date]
                if end_date:
                    all_conversations = [c for c in all_conversations 
                                     if c.original_update_time and c.original_update_time <= end_date]
            
            # Sort by original timestamps if requested
            if sort_by == "original_create_time":
                # Put conversations without original timestamps at the end
                if sort_order.lower() == "asc":
                    all_conversations.sort(
                        key=lambda c: (c.original_create_time is None, c.original_create_time or datetime.min)
                    )
                else:
                    all_conversations.sort(
                        key=lambda c: (c.original_create_time is None, c.original_create_time or datetime.max),
                        reverse=True
                    )
            elif sort_by == "original_update_time":
                if sort_order.lower() == "asc":
                    all_conversations.sort(
                        key=lambda c: (c.original_update_time is None, c.original_update_time or datetime.min)
                    )
                else:
                    all_conversations.sort(
                        key=lambda c: (c.original_update_time is None, c.original_update_time or datetime.max),
                        reverse=True
                    )
        
        # Update total count after post-filtering
        total_count = len(all_conversations)
        
        # Apply pagination to the filtered/sorted results
        paginated_conversations = all_conversations[offset:offset + limit]
        
        return paginated_conversations, total_count

def get_conversation(conversation_id: Union[str, uuid.UUID]) -> Optional[ConversationRead]:
    """
    Get a single conversation by ID.
    
    Args:
        conversation_id: UUID of the conversation
        
    Returns:
        ConversationRead object or None if not found
    """
    if isinstance(conversation_id, str):
        try:
            conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            return None
    
    with get_session() as session:
        conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conversation:
            return None
        
        conversation_read = ConversationRead.from_orm(conversation)
        
        # Get first and last message timestamps
        first_message = session.query(Message.created_at).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).first()
        
        last_message = session.query(Message.created_at).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).first()
        
        if first_message:
            conversation_read._first_message_time = first_message[0]
        
        if last_message:
            conversation_read._last_message_time = last_message[0]
            
        return conversation_read

def get_conversation_with_messages(conversation_id: Union[str, uuid.UUID]) -> Optional[Tuple[ConversationRead, List[MessageRead]]]:
    """
    Get a conversation with all its messages.
    
    Args:
        conversation_id: UUID of the conversation
        
    Returns:
        Tuple of (ConversationRead, list of MessageRead) or None if not found
    """
    if isinstance(conversation_id, str):
        try:
            conversation_id = uuid.UUID(conversation_id)
        except ValueError:
            return None
    
    with get_session() as session:
        conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
        
        if not conversation:
            return None
            
        messages = session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        
        if messages:
            conversation_read = ConversationRead.from_orm(conversation)
            conversation_read._first_message_time = messages[0].created_at
            conversation_read._last_message_time = messages[-1].created_at
            
            return (
                conversation_read,
                [MessageRead.from_orm(m) for m in messages]
            )
        else:
            return (
                ConversationRead.from_orm(conversation),
                []
            )

def export_conversation(conversation_id: Union[str, uuid.UUID], output_path: str) -> bool:
    """
    Export a conversation to a JSON file.
    
    Args:
        conversation_id: UUID of the conversation
        output_path: Path to save the JSON file
        
    Returns:
        True if successful, False otherwise
    """
    result = get_conversation_with_messages(conversation_id)
    
    if not result:
        return False
        
    conversation, messages = result
    
    try:
        export_conversation_to_json(conversation, messages, output_path)
        return True
    except Exception:
        return False

def get_conversation_count() -> int:
    """
    Get the total number of conversations in the database.
    
    Returns:
        Total count of conversations
    """
    with get_session() as session:
        return session.query(func.count(Conversation.id)).scalar()

def get_recent_conversations(
    limit: int = 10,
    use_original_dates: bool = True,
    date_field: str = "original_create_time"
) -> List[ConversationRead]:
    """
    Get the most recent conversations.
    
    Args:
        limit: Maximum number of conversations to return
        use_original_dates: Use original dates from meta_info when available
        date_field: Which date field to use (created_at, original_create_time, original_update_time)
        
    Returns:
        List of ConversationRead objects
    """
    if not use_original_dates or date_field == "created_at":
        # Use database sort if we're using database timestamps
        with get_session() as session:
            conversations = session.query(Conversation).order_by(
                desc(Conversation.created_at)
            ).limit(limit).all()
            
            return [ConversationRead.from_orm(c) for c in conversations]
    else:
        # For original timestamps, we need to get all, then sort in memory
        with get_session() as session:
            # Get all conversations
            conversations = session.query(Conversation).all()
            all_conversations = [ConversationRead.from_orm(c) for c in conversations]
            
            # Get first and last message timestamps for all conversations
            conversation_ids = [c.id for c in all_conversations]
            if conversation_ids:
                # Get first message time for each conversation
                first_message_query = (
                    session.query(
                        Message.conversation_id,
                        func.min(Message.created_at).label('first_message_time')
                    )
                    .filter(Message.conversation_id.in_(conversation_ids))
                    .group_by(Message.conversation_id)
                )
                first_message_times = {
                    str(cid): time for cid, time in first_message_query.all()
                }
                
                # Get last message time for each conversation
                last_message_query = (
                    session.query(
                        Message.conversation_id,
                        func.max(Message.created_at).label('last_message_time')
                    )
                    .filter(Message.conversation_id.in_(conversation_ids))
                    .group_by(Message.conversation_id)
                )
                last_message_times = {
                    str(cid): time for cid, time in last_message_query.all()
                }
                
                # Inject message timestamps into conversation objects
                for conversation in all_conversations:
                    conv_id = str(conversation.id)
                    if conv_id in first_message_times:
                        conversation._first_message_time = first_message_times[conv_id]
                    if conv_id in last_message_times:
                        conversation._last_message_time = last_message_times[conv_id]
            
            # Sort by requested field
            if date_field == "original_create_time":
                all_conversations.sort(
                    key=lambda c: (c.original_create_time is None, c.original_create_time or datetime.min),
                    reverse=True  # Descending order
                )
            elif date_field == "original_update_time":
                all_conversations.sort(
                    key=lambda c: (c.original_update_time is None, c.original_update_time or datetime.min),
                    reverse=True  # Descending order
                )
            
            # Return limited results
            return all_conversations[:limit]