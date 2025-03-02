"""
Chunk Manager for handling text chunks from messages and other sources.

This module provides a high-level interface for creating, managing, and
manipulating text chunks that are extracted from messages and other sources.
"""

import uuid
import logging
from typing import List, Dict, Any, Optional, Set, Union, Tuple
from enum import Enum
from datetime import datetime, timedelta

from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Message, Conversation, Chunk, ResultsBuffer, BufferItem
from carchive.chunk.chunker import Chunker, ChunkerOptions, ChunkType, ChunkResult
from carchive.buffer.buffer_manager import BufferManager
from carchive.buffer.schemas import BufferCreateSchema, BufferType, BufferItemSchema

logger = logging.getLogger(__name__)


class ChunkManager:
    """
    Manager for creating and working with text chunks.
    
    This class provides high-level methods for creating chunks from messages
    and other sources, as well as managing, searching, and processing chunks.
    """
    
    @staticmethod
    def create_chunks_from_message(
        message_id: uuid.UUID,
        chunk_type: Union[str, ChunkType] = ChunkType.PARAGRAPH,
        options: Dict[str, Any] = None,
        buffer_name: Optional[str] = None
    ) -> ChunkResult:
        """
        Create chunks from a message and optionally add them to a buffer.
        
        Args:
            message_id: UUID of the message to chunk
            chunk_type: Type of chunking strategy to use
            options: Additional options for the chunker
            buffer_name: Optional name of buffer to add chunks to
            
        Returns:
            A ChunkResult containing the created chunks and metadata
        """
        # Convert string chunk_type to enum if needed
        if isinstance(chunk_type, str):
            try:
                chunk_type = ChunkType(chunk_type)
            except ValueError:
                logger.error(f"Invalid chunk type: {chunk_type}")
                chunk_type = ChunkType.PARAGRAPH
        
        # Set up chunker options
        chunker_options = ChunkerOptions(chunk_type=chunk_type)
        
        # Apply additional options if provided
        if options:
            for key, value in options.items():
                if hasattr(chunker_options, key):
                    setattr(chunker_options, key, value)
        
        # Create chunks
        result = Chunker.chunk_message(message_id, chunker_options)
        
        # Add to buffer if specified
        if buffer_name and result.count > 0:
            ChunkManager.add_chunks_to_buffer(
                [chunk.id for chunk in result.chunks],
                buffer_name
            )
        
        return result
    
    @staticmethod
    def create_chunks_from_text(
        text: str,
        chunk_type: Union[str, ChunkType] = ChunkType.PARAGRAPH,
        options: Dict[str, Any] = None,
        save_to_db: bool = False,
        source_id: Optional[Union[uuid.UUID, str]] = None,
        buffer_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from arbitrary text.
        
        Args:
            text: Text content to chunk
            chunk_type: Type of chunking strategy to use
            options: Additional options for the chunker
            save_to_db: Whether to save chunks to the database
            source_id: Optional ID to associate with chunks
            buffer_name: Optional name of buffer to add chunks to
            
        Returns:
            List of chunk dictionaries
        """
        # Convert string chunk_type to enum if needed
        if isinstance(chunk_type, str):
            try:
                chunk_type = ChunkType(chunk_type)
            except ValueError:
                logger.error(f"Invalid chunk type: {chunk_type}")
                chunk_type = ChunkType.PARAGRAPH
        
        # Set up chunker options
        chunker_options = ChunkerOptions(chunk_type=chunk_type)
        
        # Apply additional options if provided
        if options:
            for key, value in options.items():
                if hasattr(chunker_options, key):
                    setattr(chunker_options, key, value)
        
        # Create chunks
        chunk_dicts = Chunker.chunk_text(
            text, chunker_options, source_id, save_to_db
        )
        
        # Add to buffer if specified and saved to DB
        if buffer_name and save_to_db and source_id:
            with get_session() as session:
                # Get created chunks
                if isinstance(source_id, uuid.UUID):
                    # Message chunks
                    chunks = session.query(Chunk).filter(
                        Chunk.message_id == source_id
                    ).all()
                else:
                    # External chunks, need to find by meta_info
                    chunks = session.query(Chunk).filter(
                        Chunk.meta_info['source_id'].astext == str(source_id)
                    ).all()
                
                # Add to buffer
                if chunks:
                    ChunkManager.add_chunks_to_buffer(
                        [chunk.id for chunk in chunks],
                        buffer_name
                    )
        
        return chunk_dicts
    
    @staticmethod
    def create_chunks_from_messages(
        message_ids: List[uuid.UUID],
        chunk_type: Union[str, ChunkType] = ChunkType.PARAGRAPH,
        options: Dict[str, Any] = None,
        buffer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create chunks from multiple messages.
        
        Args:
            message_ids: List of message UUIDs to chunk
            chunk_type: Type of chunking strategy to use
            options: Additional options for the chunker
            buffer_name: Optional name of buffer to add chunks to
            
        Returns:
            Dictionary with summary of results
        """
        # Create buffer first if specified
        buffer_id = None
        if buffer_name:
            with get_session() as session:
                # Check if buffer exists
                buffer = session.query(ResultsBuffer).filter(
                    ResultsBuffer.name == buffer_name
                ).first()
                
                if not buffer:
                    # Create buffer
                    buffer_data = BufferCreateSchema(
                        name=buffer_name,
                        buffer_type=BufferType.SESSION,
                        description=f"Chunks created from {len(message_ids)} messages"
                    )
                    buffer = BufferManager.create_buffer(buffer_data)
                
                buffer_id = buffer.id
        
        # Create chunks for each message
        results = {
            "total_messages": len(message_ids),
            "success_count": 0,
            "failure_count": 0,
            "total_chunks": 0,
            "failures": [],
            "buffer_id": str(buffer_id) if buffer_id else None,
            "buffer_name": buffer_name
        }
        
        for message_id in message_ids:
            try:
                result = ChunkManager.create_chunks_from_message(
                    message_id, chunk_type, options
                )
                
                if result.count > 0:
                    results["success_count"] += 1
                    results["total_chunks"] += result.count
                    
                    # Add to buffer if specified
                    if buffer_id and not buffer_name:  # Only add if we didn't specify buffer in create_chunks_from_message
                        ChunkManager.add_chunks_to_buffer(
                            [chunk.id for chunk in result.chunks],
                            buffer_id=buffer_id
                        )
                else:
                    results["failure_count"] += 1
                    results["failures"].append({
                        "message_id": str(message_id),
                        "error": "No chunks created"
                    })
            except Exception as e:
                results["failure_count"] += 1
                results["failures"].append({
                    "message_id": str(message_id),
                    "error": str(e)
                })
                logger.error(f"Error creating chunks for message {message_id}: {e}")
        
        return results
    
    @staticmethod
    def create_chunks_from_conversation(
        conversation_id: uuid.UUID,
        message_types: List[str] = None,  # e.g., ["user", "assistant"]
        chunk_type: Union[str, ChunkType] = ChunkType.PARAGRAPH,
        options: Dict[str, Any] = None,
        buffer_name: Optional[str] = None,
        max_messages: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create chunks from all messages in a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            message_types: Optional list of message types to include
            chunk_type: Type of chunking strategy to use
            options: Additional options for the chunker
            buffer_name: Optional name of buffer to add chunks to
            max_messages: Maximum number of messages to process
            
        Returns:
            Dictionary with summary of results
        """
        with get_session() as session:
            # Get message IDs
            query = session.query(Message.id).filter(
                Message.conversation_id == conversation_id
            )
            
            # Filter by message type if specified
            if message_types:
                query = query.filter(Message.role.in_(message_types))
            
            # Order by position or creation time
            query = query.order_by(
                func.coalesce(Message.position, 0).asc(),
                Message.created_at.asc()
            )
            
            # Limit if specified
            if max_messages:
                query = query.limit(max_messages)
            
            # Get message IDs
            message_ids = [mid[0] for mid in query.all()]
        
        # Create chunks from messages
        return ChunkManager.create_chunks_from_messages(
            message_ids, chunk_type, options, buffer_name
        )
    
    @staticmethod
    def add_chunks_to_buffer(
        chunk_ids: List[uuid.UUID],
        buffer_name: Optional[str] = None,
        buffer_id: Optional[uuid.UUID] = None
    ) -> int:
        """
        Add chunks to a buffer.
        
        Args:
            chunk_ids: List of chunk UUIDs to add
            buffer_name: Name of the buffer to add to
            buffer_id: UUID of the buffer to add to
            
        Returns:
            Number of chunks added
        """
        if not chunk_ids:
            return 0
        
        # Get buffer by name or ID
        if buffer_name and not buffer_id:
            buffer = BufferManager.get_buffer_by_name(buffer_name)
            if not buffer:
                # Create buffer
                buffer_data = BufferCreateSchema(
                    name=buffer_name,
                    buffer_type=BufferType.SESSION,
                    description=f"Buffer for chunks"
                )
                buffer = BufferManager.create_buffer(buffer_data)
            
            buffer_id = buffer.id
        
        if not buffer_id:
            logger.error("No buffer specified")
            return 0
        
        # Create buffer items
        buffer_items = [
            BufferItemSchema(
                chunk_id=chunk_id,
                position=i
            )
            for i, chunk_id in enumerate(chunk_ids)
        ]
        
        # Add to buffer
        return BufferManager.add_items_to_buffer(buffer_id, buffer_items)
    
    @staticmethod
    def get_chunks_by_message(
        message_id: uuid.UUID, 
        chunk_type: Optional[Union[str, ChunkType]] = None
    ) -> List[Chunk]:
        """
        Get all chunks associated with a message.
        
        Args:
            message_id: UUID of the message
            chunk_type: Optional type of chunks to retrieve
            
        Returns:
            List of chunks
        """
        with get_session() as session:
            query = session.query(Chunk).filter(Chunk.message_id == message_id)
            
            # Filter by chunk type if specified
            if chunk_type:
                if isinstance(chunk_type, str):
                    query = query.filter(Chunk.chunk_type == chunk_type)
                else:
                    query = query.filter(Chunk.chunk_type == chunk_type.value)
            
            # Order by position
            query = query.order_by(Chunk.position.asc())
            
            return query.all()
    
    @staticmethod
    def delete_chunks_by_message(message_id: uuid.UUID) -> int:
        """
        Delete all chunks associated with a message.
        
        Args:
            message_id: UUID of the message
            
        Returns:
            Number of chunks deleted
        """
        with get_session() as session:
            # Count chunks
            count = session.query(Chunk).filter(Chunk.message_id == message_id).count()
            
            # Delete chunks
            session.query(Chunk).filter(Chunk.message_id == message_id).delete()
            session.commit()
            
            return count
    
    @staticmethod
    def delete_chunks_by_conversation(conversation_id: uuid.UUID) -> int:
        """
        Delete all chunks associated with a conversation.
        
        Args:
            conversation_id: UUID of the conversation
            
        Returns:
            Number of chunks deleted
        """
        with get_session() as session:
            # Get message IDs
            message_ids = [
                mid[0] for mid in session.query(Message.id).filter(
                    Message.conversation_id == conversation_id
                ).all()
            ]
            
            # Count chunks
            count = session.query(Chunk).filter(
                Chunk.message_id.in_(message_ids)
            ).count()
            
            # Delete chunks
            session.query(Chunk).filter(
                Chunk.message_id.in_(message_ids)
            ).delete(synchronize_session=False)
            session.commit()
            
            return count
    
    @staticmethod
    def get_chunk_by_id(chunk_id: uuid.UUID) -> Optional[Chunk]:
        """
        Get a chunk by ID.
        
        Args:
            chunk_id: UUID of the chunk
            
        Returns:
            Chunk if found, None otherwise
        """
        with get_session() as session:
            return session.query(Chunk).filter(Chunk.id == chunk_id).first()
    
    @staticmethod
    def search_chunks(
        query: str,
        exact: bool = False,
        limit: int = 100,
        chunk_type: Optional[Union[str, ChunkType]] = None,
        message_id: Optional[uuid.UUID] = None,
        conversation_id: Optional[uuid.UUID] = None
    ) -> List[Chunk]:
        """
        Search for chunks by content.
        
        Args:
            query: Search query
            exact: Whether to perform exact match
            limit: Maximum number of results
            chunk_type: Optional type of chunks to search
            message_id: Optional message ID to filter by
            conversation_id: Optional conversation ID to filter by
            
        Returns:
            List of matching chunks
        """
        with get_session() as session:
            # Build query
            db_query = session.query(Chunk)
            
            # Add content filter
            if exact:
                db_query = db_query.filter(Chunk.content == query)
            else:
                db_query = db_query.filter(Chunk.content.ilike(f"%{query}%"))
            
            # Filter by chunk type if specified
            if chunk_type:
                if isinstance(chunk_type, str):
                    db_query = db_query.filter(Chunk.chunk_type == chunk_type)
                else:
                    db_query = db_query.filter(Chunk.chunk_type == chunk_type.value)
            
            # Filter by message ID if specified
            if message_id:
                db_query = db_query.filter(Chunk.message_id == message_id)
            
            # Filter by conversation ID if specified
            if conversation_id:
                # Get message IDs in conversation
                message_ids = [
                    mid[0] for mid in session.query(Message.id).filter(
                        Message.conversation_id == conversation_id
                    ).all()
                ]
                db_query = db_query.filter(Chunk.message_id.in_(message_ids))
            
            # Order by position instead of trying to use position() function
            # which isn't standardized across database backends
            db_query = db_query.order_by(
                Chunk.position.asc()
            )
            
            # Limit results
            db_query = db_query.limit(limit)
            
            return db_query.all()
    
    @staticmethod
    def rechunk_message(
        message_id: uuid.UUID,
        new_chunk_type: Union[str, ChunkType],
        options: Dict[str, Any] = None,
        buffer_name: Optional[str] = None
    ) -> ChunkResult:
        """
        Delete existing chunks for a message and create new ones.
        
        Args:
            message_id: UUID of the message to rechunk
            new_chunk_type: Type of chunking strategy to use
            options: Additional options for the chunker
            buffer_name: Optional name of buffer to add chunks to
            
        Returns:
            A ChunkResult containing the created chunks and metadata
        """
        # Delete existing chunks
        ChunkManager.delete_chunks_by_message(message_id)
        
        # Create new chunks
        return ChunkManager.create_chunks_from_message(
            message_id, new_chunk_type, options, buffer_name
        )
    
    @staticmethod
    def get_chunk_stats() -> Dict[str, Any]:
        """
        Get statistics about chunks in the database.
        
        Returns:
            Dictionary with chunk statistics
        """
        with get_session() as session:
            # Total chunks
            total_chunks = session.query(func.count(Chunk.id)).scalar()
            
            # Chunks by type
            chunks_by_type = {}
            for chunk_type in [ct.value for ct in ChunkType]:
                count = session.query(func.count(Chunk.id)).filter(
                    Chunk.chunk_type == chunk_type
                ).scalar()
                chunks_by_type[chunk_type] = count
            
            # Recent chunks
            recent_time = datetime.now() - timedelta(days=7)
            recent_chunks = session.query(func.count(Chunk.id)).filter(
                Chunk.created_at >= recent_time
            ).scalar()
            
            # Average chunk length
            avg_length = session.query(func.avg(func.length(Chunk.content))).scalar()
            
            # Messages with chunks
            messages_with_chunks = session.query(
                func.count(func.distinct(Chunk.message_id))
            ).scalar()
            
            return {
                "total_chunks": total_chunks,
                "chunks_by_type": chunks_by_type,
                "recent_chunks": recent_chunks,
                "avg_chunk_length": float(avg_length) if avg_length else 0,
                "messages_with_chunks": messages_with_chunks
            }