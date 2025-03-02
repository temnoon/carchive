"""
Buffer Manager for handling search results and other collections of entities.

This module provides functions for creating, managing, and operating on results buffers,
which can store search results and other collections of entities for multi-step workflows.
"""

import uuid
import logging
import time
import os
from typing import List, Optional, Dict, Any, Type, Union, cast
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, and_
from sqlalchemy.sql.expression import BinaryExpression

from carchive.database.session import get_session
from carchive.database.models import (
    ResultsBuffer, BufferItem, Message, Conversation, Chunk, AgentOutput
)
from carchive.buffer.schemas import (
    BufferCreateSchema, BufferUpdateSchema, BufferFilterCriteria,
    BufferType, BufferItemSchema, BufferRead, BufferDetailedRead
)
from carchive.schemas.db_objects import (
    DBObject, MessageRead, ConversationRead, ChunkRead, CollectionRead
)
from carchive.utils.conversions import convert_to_pydantic

logger = logging.getLogger(__name__)

class BufferManager:
    """
    Manager for results buffers that store search results and other entities.
    
    This class provides methods for creating, updating, and operating on buffers
    of search results and other collections of entities.
    """
    
    @staticmethod
    def _generate_session_id() -> str:
        """
        Generate a unique session ID for CLI session tracking.
        
        For persistence across CLI commands, we use a combination of:
        1. The user's username 
        2. The current terminal session ID
        3. A fallback to a file-based session ID if those aren't available
        
        Returns:
            A unique session identifier string
        """
        # Try to get username
        username = os.environ.get('USER') or os.environ.get('USERNAME')
        
        # Try to get terminal session ID (works in most Unix environments)
        term_session = os.environ.get('TERM_SESSION_ID')
        
        if username and term_session:
            return f"{username}:{term_session}"
        
        # Fallback: Check for a session file or create one
        session_dir = os.path.expanduser("~/.carchive")
        session_file = os.path.join(session_dir, "session_id")
        
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
            
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                session_id = f.read().strip()
                if session_id:
                    return session_id
        
        # Generate a new session ID
        session_id = f"cli-{int(time.time())}-{str(uuid.uuid4())[:8]}"
        with open(session_file, 'w') as f:
            f.write(session_id)
            
        return session_id
    
    @staticmethod
    def create_buffer(buffer_data: BufferCreateSchema) -> ResultsBuffer:
        """
        Create a new buffer with optional initial items.
        
        Args:
            buffer_data: The buffer creation parameters
            
        Returns:
            The newly created buffer
        """
        with get_session() as session:
            # Apply session ID if it's a session buffer but no ID was provided
            if buffer_data.buffer_type == BufferType.SESSION and not buffer_data.session_id:
                buffer_data.session_id = BufferManager._generate_session_id()
                
            # Create the buffer
            new_buffer = ResultsBuffer(
                name=buffer_data.name,
                buffer_type=buffer_data.buffer_type.value,
                session_id=buffer_data.session_id,
                description=buffer_data.description,
                meta_info=buffer_data.meta_info or {}
            )
            session.add(new_buffer)
            session.flush()
            
            # Add items if provided
            if buffer_data.items:
                for pos, item in enumerate(buffer_data.items):
                    buffer_item = BufferItem(
                        buffer_id=new_buffer.id,
                        message_id=item.message_id,
                        conversation_id=item.conversation_id,
                        chunk_id=item.chunk_id,
                        gencom_id=item.gencom_id,
                        position=item.position or pos,
                        meta_info=item.meta_info or {}
                    )
                    session.add(buffer_item)
            
            session.commit()
            session.refresh(new_buffer)
            return new_buffer
    
    @staticmethod
    def get_buffer_by_name(name: str, session_id: Optional[str] = None) -> Optional[ResultsBuffer]:
        """
        Retrieve a buffer by name and optional session ID.
        
        Args:
            name: The name of the buffer to retrieve
            session_id: Optional session ID (for session-scoped buffers)
            
        Returns:
            The buffer if found, None otherwise
        """
        with get_session() as session:
            query = session.query(ResultsBuffer).filter(ResultsBuffer.name == name)
            
            # If session ID is provided, filter by it
            if session_id:
                query = query.filter(ResultsBuffer.session_id == session_id)
            
            return query.first()
    
    @staticmethod
    def get_buffer(buffer_id: uuid.UUID) -> Optional[ResultsBuffer]:
        """
        Retrieve a buffer by ID.
        
        Args:
            buffer_id: The UUID of the buffer to retrieve
            
        Returns:
            The buffer if found, None otherwise
        """
        with get_session() as session:
            return session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
    
    @staticmethod
    def list_buffers(session_id: Optional[str] = None, buffer_type: Optional[str] = None) -> List[ResultsBuffer]:
        """
        List all buffers, optionally filtered by session ID or buffer type.
        
        Args:
            session_id: Optional session ID to filter by
            buffer_type: Optional buffer type to filter by
            
        Returns:
            List of matching buffers
        """
        with get_session() as session:
            query = session.query(ResultsBuffer)
            
            # Apply filters if provided
            if session_id:
                query = query.filter(ResultsBuffer.session_id == session_id)
            if buffer_type:
                query = query.filter(ResultsBuffer.buffer_type == buffer_type)
                
            return query.order_by(ResultsBuffer.created_at.desc()).all()
    
    @staticmethod
    def update_buffer(buffer_id: uuid.UUID, update_data: BufferUpdateSchema) -> Optional[ResultsBuffer]:
        """
        Update a buffer's metadata.
        
        Args:
            buffer_id: The UUID of the buffer to update
            update_data: The fields to update
            
        Returns:
            The updated buffer or None if not found
        """
        with get_session() as session:
            buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not buffer:
                return None
            
            # Update fields if provided
            if update_data.name is not None:
                buffer.name = update_data.name
            if update_data.description is not None:
                buffer.description = update_data.description
            if update_data.meta_info is not None:
                buffer.meta_info = update_data.meta_info
            
            buffer.updated_at = datetime.now()
            session.commit()
            session.refresh(buffer)
            return buffer
    
    @staticmethod
    def delete_buffer(buffer_id: uuid.UUID) -> bool:
        """
        Delete a buffer and all its items.
        
        Args:
            buffer_id: The UUID of the buffer to delete
            
        Returns:
            True if deleted, False if not found
        """
        with get_session() as session:
            buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not buffer:
                return False
            
            session.delete(buffer)
            session.commit()
            return True
    
    @staticmethod
    def clear_buffer(buffer_id: uuid.UUID) -> bool:
        """
        Remove all items from a buffer without deleting the buffer itself.
        
        Args:
            buffer_id: The UUID of the buffer to clear
            
        Returns:
            True if cleared, False if not found
        """
        with get_session() as session:
            buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not buffer:
                return False
            
            # Delete all items
            session.query(BufferItem).filter(BufferItem.buffer_id == buffer_id).delete()
            buffer.updated_at = datetime.now()
            session.commit()
            return True
    
    @staticmethod
    def add_items_to_buffer(buffer_id: uuid.UUID, items: List[BufferItemSchema]) -> int:
        """
        Add items to an existing buffer.
        
        Args:
            buffer_id: The UUID of the buffer to add items to
            items: The items to add
            
        Returns:
            The number of items added
        """
        with get_session() as session:
            buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not buffer:
                return 0
            
            # Find current max position
            max_pos_result = session.query(func.max(BufferItem.position)).filter(
                BufferItem.buffer_id == buffer_id
            ).first()
            
            max_pos = max_pos_result[0] if max_pos_result[0] is not None else -1
            
            # Add new items starting from max_pos + 1
            added_count = 0
            for i, item in enumerate(items):
                buffer_item = BufferItem(
                    buffer_id=buffer_id,
                    message_id=item.message_id,
                    conversation_id=item.conversation_id,
                    chunk_id=item.chunk_id,
                    gencom_id=item.gencom_id,
                    position=item.position if item.position is not None else max_pos + i + 1,
                    meta_info=item.meta_info or {}
                )
                session.add(buffer_item)
                added_count += 1
                
            buffer.updated_at = datetime.now()
            session.commit()
            return added_count
    
    @staticmethod
    def add_search_results(
        buffer_id: uuid.UUID, 
        results: List[DBObject]
    ) -> int:
        """
        Add search results to a buffer.
        
        Args:
            buffer_id: The UUID of the buffer to add results to
            results: The search results to add
            
        Returns:
            The number of items added
        """
        items = []
        for obj in results:
            item = BufferItemSchema()
            
            # Determine type and set the appropriate ID
            if isinstance(obj, MessageRead):
                item.message_id = obj.id
                if hasattr(obj, 'meta_info') and obj.meta_info and 'conversation_id' in obj.meta_info:
                    item.conversation_id = obj.meta_info['conversation_id']
            elif isinstance(obj, ConversationRead):
                item.conversation_id = obj.id
            elif isinstance(obj, ChunkRead):
                item.chunk_id = obj.id
            elif hasattr(obj, 'target_type') and hasattr(obj, 'id'):
                # This is likely an AgentOutput (gencom)
                item.gencom_id = obj.id
            else:
                # Log the unknown type and skip it
                logger.warning(f"Unsupported object type in add_search_results: {type(obj)}")
                continue
                
            items.append(item)
            
        return BufferManager.add_items_to_buffer(buffer_id, items)
    
    @staticmethod
    def filter_buffer(
        buffer_id: uuid.UUID, 
        filter_criteria: BufferFilterCriteria,
        target_buffer_id: Optional[uuid.UUID] = None
    ) -> Union[uuid.UUID, int]:
        """
        Filter a buffer's contents by criteria and store results in a new or existing buffer.
        
        Args:
            buffer_id: The UUID of the source buffer
            filter_criteria: Filtering criteria
            target_buffer_id: Optional UUID of a target buffer to store results
            
        Returns:
            If target_buffer_id is None, returns a new buffer's UUID
            If target_buffer_id is provided, returns the count of items added
        """
        with get_session() as session:
            # Get source buffer
            source_buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not source_buffer:
                raise ValueError(f"Source buffer with ID {buffer_id} not found")
            
            # Build the query for filtered items
            query = session.query(BufferItem).filter(BufferItem.buffer_id == buffer_id)
            
            # Apply filters
            filters = []
            
            # Role filter (applies to messages)
            if filter_criteria.role:
                # Get message IDs with matching role
                message_subq = session.query(Message.id).filter(
                    Message.role == filter_criteria.role
                ).subquery()
                
                filters.append(BufferItem.message_id.in_(message_subq))
            
            # Content filter (applies to messages, conversations, chunks)
            if filter_criteria.content:
                # Build content filter for messages
                message_content_subq = session.query(Message.id).filter(
                    Message.content.ilike(f"%{filter_criteria.content}%")
                ).subquery()
                
                # Build content filter for conversations (title)
                convo_content_subq = session.query(Conversation.id).filter(
                    Conversation.title.ilike(f"%{filter_criteria.content}%")
                ).subquery()
                
                # Build content filter for chunks
                chunk_content_subq = session.query(Chunk.id).filter(
                    Chunk.content.ilike(f"%{filter_criteria.content}%")
                ).subquery()
                
                filters.append(or_(
                    BufferItem.message_id.in_(message_content_subq),
                    BufferItem.conversation_id.in_(convo_content_subq),
                    BufferItem.chunk_id.in_(chunk_content_subq)
                ))
                
            # Days filter (applies to all)
            if filter_criteria.days:
                from datetime import datetime, timedelta
                
                cutoff_date = datetime.now() - timedelta(days=filter_criteria.days)
                
                # Get messages created after cutoff
                message_date_subq = session.query(Message.id).filter(
                    Message.created_at >= cutoff_date
                ).subquery()
                
                # Get conversations created after cutoff
                convo_date_subq = session.query(Conversation.id).filter(
                    Conversation.created_at >= cutoff_date
                ).subquery()
                
                # Get chunks created after cutoff
                chunk_date_subq = session.query(Chunk.id).filter(
                    Chunk.created_at >= cutoff_date
                ).subquery()
                
                filters.append(or_(
                    BufferItem.message_id.in_(message_date_subq),
                    BufferItem.conversation_id.in_(convo_date_subq),
                    BufferItem.chunk_id.in_(chunk_date_subq)
                ))
                
            # Images filter (applies to messages with image attachments)
            if filter_criteria.has_image is not None:
                # This requires a more complex query using MessageMedia and Media
                from carchive.database.models import MessageMedia, Media
                
                if filter_criteria.has_image:
                    # Messages with image attachments
                    image_message_subq = session.query(MessageMedia.message_id).join(
                        Media, MessageMedia.media_id == Media.id
                    ).filter(
                        Media.media_type == 'image'
                    ).subquery()
                    
                    filters.append(BufferItem.message_id.in_(image_message_subq))
                else:
                    # Messages without image attachments
                    # This is more complex - we need messages not in the image_message_subq
                    image_message_subq = session.query(MessageMedia.message_id).join(
                        Media, MessageMedia.media_id == Media.id
                    ).filter(
                        Media.media_type == 'image'
                    ).subquery()
                    
                    # Messages that have no entries in MessageMedia table or have no image entries
                    message_without_images_subq = session.query(Message.id).outerjoin(
                        MessageMedia, Message.id == MessageMedia.message_id
                    ).filter(
                        or_(
                            MessageMedia.message_id.is_(None),
                            ~Message.id.in_(image_message_subq)
                        )
                    ).subquery()
                    
                    filters.append(BufferItem.message_id.in_(message_without_images_subq))
            
            # Exclusion filter
            if filter_criteria.exclude_ids:
                # Convert string IDs to UUIDs if needed
                exclude_ids = [
                    uuid.UUID(id_str) if isinstance(id_str, str) else id_str 
                    for id_str in filter_criteria.exclude_ids
                ]
                
                # Exclude items with matching conversation, message, or chunk IDs
                filters.append(and_(
                    BufferItem.conversation_id.notin_(exclude_ids),
                    BufferItem.message_id.notin_(exclude_ids),
                    BufferItem.chunk_id.notin_(exclude_ids)
                ))
            
            # Apply all filters if present
            if filters:
                query = query.filter(and_(*filters))
            
            # Run the query and get filtered items
            filtered_items = query.all()
            
            # If no target buffer specified, create a new one
            if target_buffer_id is None:
                # Create a new buffer with the filtered items
                new_buffer = ResultsBuffer(
                    name=f"{source_buffer.name}_filtered",
                    buffer_type=source_buffer.buffer_type,
                    session_id=source_buffer.session_id,
                    description=f"Filtered from {source_buffer.name}",
                    meta_info=source_buffer.meta_info.copy() if source_buffer.meta_info else {}
                )
                session.add(new_buffer)
                session.flush()
                
                # Add filtered items to new buffer
                for pos, item in enumerate(filtered_items):
                    buffer_item = BufferItem(
                        buffer_id=new_buffer.id,
                        message_id=item.message_id,
                        conversation_id=item.conversation_id,
                        chunk_id=item.chunk_id,
                        gencom_id=item.gencom_id,
                        position=pos,
                        meta_info=item.meta_info.copy() if item.meta_info else {}
                    )
                    session.add(buffer_item)
                
                session.commit()
                return new_buffer.id
            else:
                # Add filtered items to target buffer
                target_buffer = session.query(ResultsBuffer).filter(
                    ResultsBuffer.id == target_buffer_id
                ).first()
                
                if not target_buffer:
                    raise ValueError(f"Target buffer with ID {target_buffer_id} not found")
                
                # Find current max position
                max_pos_result = session.query(func.max(BufferItem.position)).filter(
                    BufferItem.buffer_id == target_buffer_id
                ).first()
                
                max_pos = max_pos_result[0] if max_pos_result[0] is not None else -1
                
                # Add filtered items to target buffer
                added_count = 0
                for i, item in enumerate(filtered_items):
                    buffer_item = BufferItem(
                        buffer_id=target_buffer_id,
                        message_id=item.message_id,
                        conversation_id=item.conversation_id,
                        chunk_id=item.chunk_id,
                        gencom_id=item.gencom_id,
                        position=max_pos + i + 1,
                        meta_info=item.meta_info.copy() if item.meta_info else {}
                    )
                    session.add(buffer_item)
                    added_count += 1
                
                target_buffer.updated_at = datetime.now()
                session.commit()
                return added_count
    
    @staticmethod
    def merge_buffers(
        source_buffer_ids: List[uuid.UUID],
        target_buffer_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        deduplicate: bool = True
    ) -> Union[uuid.UUID, int]:
        """
        Merge multiple buffers into a new or existing buffer.
        
        Args:
            source_buffer_ids: List of buffer UUIDs to merge
            target_buffer_id: Optional target buffer UUID to merge into
            name: Optional name for the new buffer (if target_buffer_id is None)
            deduplicate: Whether to remove duplicate items
            
        Returns:
            If target_buffer_id is None, returns a new buffer's UUID
            If target_buffer_id is provided, returns the count of items added
        """
        with get_session() as session:
            # Verify all source buffers exist
            source_buffers = []
            for bid in source_buffer_ids:
                buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == bid).first()
                if not buffer:
                    raise ValueError(f"Source buffer with ID {bid} not found")
                source_buffers.append(buffer)
            
            if not source_buffers:
                raise ValueError("No valid source buffers provided")
            
            # Get default name and session ID from first buffer if not provided
            default_name = name or f"Merged_{source_buffers[0].name}"
            default_session_id = source_buffers[0].session_id
            
            # Collect all items from all source buffers
            all_items = []
            for buffer in source_buffers:
                items = session.query(BufferItem).filter(BufferItem.buffer_id == buffer.id).all()
                all_items.extend(items)
            
            # Deduplicate items if requested
            if deduplicate:
                # Create sets to track unique entities
                unique_message_ids = set()
                unique_conversation_ids = set()
                unique_chunk_ids = set()
                unique_gencom_ids = set()
                
                # Filter items to only include unique entities
                unique_items = []
                for item in all_items:
                    # Track each type of entity
                    if item.message_id:
                        if item.message_id in unique_message_ids:
                            continue
                        unique_message_ids.add(item.message_id)
                    elif item.conversation_id:
                        if item.conversation_id in unique_conversation_ids:
                            continue
                        unique_conversation_ids.add(item.conversation_id)
                    elif item.chunk_id:
                        if item.chunk_id in unique_chunk_ids:
                            continue
                        unique_chunk_ids.add(item.chunk_id)
                    elif item.gencom_id:
                        if item.gencom_id in unique_gencom_ids:
                            continue
                        unique_gencom_ids.add(item.gencom_id)
                    else:
                        # Skip items with no entity ID
                        continue
                    
                    unique_items.append(item)
                
                # Use deduplicated items
                all_items = unique_items
            
            # If no target buffer specified, create a new one
            if target_buffer_id is None:
                # Create a new buffer with the merged items
                new_buffer = ResultsBuffer(
                    name=default_name,
                    buffer_type=source_buffers[0].buffer_type,
                    session_id=default_session_id,
                    description=f"Merged from {len(source_buffers)} buffers",
                    meta_info={}
                )
                session.add(new_buffer)
                session.flush()
                
                # Add merged items to new buffer
                for pos, item in enumerate(all_items):
                    buffer_item = BufferItem(
                        buffer_id=new_buffer.id,
                        message_id=item.message_id,
                        conversation_id=item.conversation_id,
                        chunk_id=item.chunk_id,
                        gencom_id=item.gencom_id,
                        position=pos,
                        meta_info=item.meta_info.copy() if item.meta_info else {}
                    )
                    session.add(buffer_item)
                
                session.commit()
                return new_buffer.id
            else:
                # Add merged items to target buffer
                target_buffer = session.query(ResultsBuffer).filter(
                    ResultsBuffer.id == target_buffer_id
                ).first()
                
                if not target_buffer:
                    raise ValueError(f"Target buffer with ID {target_buffer_id} not found")
                
                # Find current max position
                max_pos_result = session.query(func.max(BufferItem.position)).filter(
                    BufferItem.buffer_id == target_buffer_id
                ).first()
                
                max_pos = max_pos_result[0] if max_pos_result[0] is not None else -1
                
                # Add merged items to target buffer
                added_count = 0
                for i, item in enumerate(all_items):
                    buffer_item = BufferItem(
                        buffer_id=target_buffer_id,
                        message_id=item.message_id,
                        conversation_id=item.conversation_id,
                        chunk_id=item.chunk_id,
                        gencom_id=item.gencom_id,
                        position=max_pos + i + 1,
                        meta_info=item.meta_info.copy() if item.meta_info else {}
                    )
                    session.add(buffer_item)
                    added_count += 1
                
                target_buffer.updated_at = datetime.now()
                session.commit()
                return added_count
    
    @staticmethod
    def get_buffer_contents_as_dbobjects(buffer_id: uuid.UUID) -> List[DBObject]:
        """
        Retrieve the contents of a buffer as DBObject instances.
        
        Args:
            buffer_id: The UUID of the buffer to retrieve contents from
            
        Returns:
            A list of DBObject instances (MessageRead, ConversationRead, etc.)
        """
        with get_session() as session:
            # Get all items in this buffer
            items = session.query(BufferItem).filter(
                BufferItem.buffer_id == buffer_id
            ).order_by(BufferItem.position).all()
            
            results = []
            for item in items:
                # Fetch the appropriate entity based on which ID is set
                if item.message_id:
                    entity = session.query(Message).filter(Message.id == item.message_id).first()
                    if entity:
                        results.append(convert_to_pydantic(entity))
                elif item.conversation_id:
                    entity = session.query(Conversation).filter(Conversation.id == item.conversation_id).first()
                    if entity:
                        results.append(convert_to_pydantic(entity))
                elif item.chunk_id:
                    entity = session.query(Chunk).filter(Chunk.id == item.chunk_id).first()
                    if entity:
                        results.append(convert_to_pydantic(entity))
                elif item.gencom_id:
                    entity = session.query(AgentOutput).filter(AgentOutput.id == item.gencom_id).first()
                    if entity:
                        # Handle AgentOutput directly
                        from carchive.schemas.db_objects import DBObject
                        
                        class AgentOutputRead(DBObject):
                            content: str
                            output_type: str
                            target_type: str
                            target_id: uuid.UUID
                            agent_name: str
                            
                        gencom_obj = AgentOutputRead(
                            id=entity.id,
                            created_at=entity.created_at,
                            content=entity.content,
                            output_type=entity.output_type,
                            target_type=entity.target_type,
                            target_id=entity.target_id,
                            agent_name=entity.agent_name
                        )
                        results.append(gencom_obj)
            
            return results
    
    @staticmethod
    def get_buffer_with_contents(buffer_id: uuid.UUID) -> Optional[BufferDetailedRead]:
        """
        Get a buffer with all its contents.
        
        Args:
            buffer_id: The UUID of the buffer to retrieve
            
        Returns:
            A BufferDetailedRead instance or None if not found
        """
        with get_session() as session:
            buffer = session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer_id).first()
            if not buffer:
                return None
            
            # Get the contents as DBObjects
            items = BufferManager.get_buffer_contents_as_dbobjects(buffer_id)
            
            # Count total items
            item_count = session.query(BufferItem).filter(BufferItem.buffer_id == buffer_id).count()
            
            # Convert to Pydantic model
            buffer_data = BufferDetailedRead(
                id=buffer.id,
                name=buffer.name,
                buffer_type=buffer.buffer_type,
                session_id=buffer.session_id,
                description=buffer.description,
                item_count=item_count,
                created_at=buffer.created_at,
                updated_at=buffer.updated_at,
                meta_info=buffer.meta_info,
                items=items
            )
            
            return buffer_data
    
    @staticmethod
    def convert_buffer_to_collection(
        buffer_id: uuid.UUID, 
        collection_name: str,
        description: Optional[str] = None
    ) -> uuid.UUID:
        """
        Convert a buffer to a collection.
        
        Args:
            buffer_id: The UUID of the buffer to convert
            collection_name: The name for the new collection
            description: Optional description for the collection
            
        Returns:
            The UUID of the newly created collection
        """
        from carchive.collections.collection_manager import CollectionManager
        from carchive.collections.schemas import CollectionCreateSchema, CollectionItemSchema
        
        # Get buffer contents as DBObjects
        buffer_objects = BufferManager.get_buffer_contents_as_dbobjects(buffer_id)
        
        # Create collection using CollectionManager
        return CollectionManager.create_collection_from_dbobjects(
            name=collection_name,
            objects=buffer_objects,
            meta_info={"description": description} if description else None
        ).id