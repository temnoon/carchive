"""
Tests for the chunk manager functionality.
"""

import uuid
import pytest
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from carchive.chunk.chunker import Chunker, ChunkType, ChunkerOptions
from carchive.chunk.manager import ChunkManager
from carchive.database.models import Message, Chunk, ResultsBuffer, BufferItem
from carchive.database.session import get_session


def create_test_message() -> Message:
    """Create a test message in the database for chunk testing."""
    with get_session() as session:
        # First try to get an existing test message
        msg = session.query(Message).filter(
            Message.content.like("%This is a test message for chunking%")
        ).first()
        
        if msg:
            return msg
        
        # Create a multi-paragraph test message
        test_message = Message(
            role="user",
            content="""This is a test message for chunking.

This is the second paragraph of the test message. It contains multiple
sentences with different lengths. This is a short one.

And this is the third paragraph. It's shorter.

Finally, a fourth paragraph for good measure.""",
            meta_info={"test": True}
        )
        
        session.add(test_message)
        session.commit()
        session.refresh(test_message)
        return test_message


def test_chunker_basic_functionality():
    """Test basic chunking functionality."""
    # Create a test message
    message = create_test_message()
    
    # Test paragraph chunking
    options = ChunkerOptions(chunk_type=ChunkType.PARAGRAPH)
    result = Chunker.chunk_message(message.id, options)
    
    # Should create 4 chunks (one per paragraph)
    assert result.count == 4
    
    # Verify the chunks contain the expected content
    chunks = result.chunks
    assert "This is a test message for chunking" in chunks[0].content
    assert "second paragraph" in chunks[1].content
    assert "third paragraph" in chunks[2].content
    assert "fourth paragraph" in chunks[3].content
    
    # Test sentence chunking
    options = ChunkerOptions(chunk_type=ChunkType.SENTENCE)
    result = Chunker.chunk_message(message.id, options)
    
    # Should create 7 chunks (one per sentence)
    assert result.count >= 6  # At least 6 sentences
    
    # Test fixed length chunking
    options = ChunkerOptions(
        chunk_type=ChunkType.FIXED_LENGTH,
        chunk_size=50,
        chunk_overlap=10
    )
    result = Chunker.chunk_message(message.id, options)
    
    # Should create several fixed-length chunks
    assert result.count > 0
    
    # Verify chunk size is respected
    for chunk in result.chunks:
        assert len(chunk.content) <= 50
        
    # Clean up chunks
    with get_session() as session:
        session.query(Chunk).filter(Chunk.message_id == message.id).delete()
        session.commit()


def test_chunk_manager_create_from_message():
    """Test ChunkManager.create_chunks_from_message."""
    # Create a test message
    message = create_test_message()
    
    # Use ChunkManager to create chunks
    result = ChunkManager.create_chunks_from_message(
        message.id,
        chunk_type=ChunkType.PARAGRAPH
    )
    
    # Should create 4 chunks (one per paragraph)
    assert result.count == 4
    
    # Create chunks and add to buffer
    buffer_name = "test_chunk_buffer"
    result = ChunkManager.create_chunks_from_message(
        message.id,
        chunk_type=ChunkType.PARAGRAPH,
        buffer_name=buffer_name
    )
    
    # Verify buffer contains the chunks
    with get_session() as session:
        buffer = session.query(ResultsBuffer).filter(
            ResultsBuffer.name == buffer_name
        ).first()
        
        assert buffer is not None
        
        # Count items in buffer
        items_count = session.query(BufferItem).filter(
            BufferItem.buffer_id == buffer.id
        ).count()
        
        assert items_count == 4
        
        # Clean up
        session.query(BufferItem).filter(BufferItem.buffer_id == buffer.id).delete()
        session.query(ResultsBuffer).filter(ResultsBuffer.id == buffer.id).delete()
        session.query(Chunk).filter(Chunk.message_id == message.id).delete()
        session.commit()


def test_chunk_manager_search():
    """Test chunk search functionality."""
    # Create a test message
    message = create_test_message()
    
    # Create chunks
    result = ChunkManager.create_chunks_from_message(
        message.id,
        chunk_type=ChunkType.PARAGRAPH
    )
    
    # Search for chunks containing "paragraph"
    chunks = ChunkManager.search_chunks("paragraph")
    
    assert len(chunks) >= 3  # At least 3 chunks should match
    
    # Search with exact match
    chunks = ChunkManager.search_chunks("third paragraph", exact=True)
    assert len(chunks) == 0  # No exact matches
    
    # Search within specific message
    chunks = ChunkManager.search_chunks("test", message_id=message.id)
    assert len(chunks) > 0
    
    # Clean up
    with get_session() as session:
        session.query(Chunk).filter(Chunk.message_id == message.id).delete()
        session.commit()


def test_chunk_manager_stats():
    """Test chunk statistics functionality."""
    # Create a test message
    message = create_test_message()
    
    # Create chunks of different types
    ChunkManager.create_chunks_from_message(message.id, chunk_type=ChunkType.PARAGRAPH)
    ChunkManager.create_chunks_from_message(message.id, chunk_type=ChunkType.SENTENCE)
    
    # Get stats
    stats = ChunkManager.get_chunk_stats()
    
    assert stats["total_chunks"] > 0
    assert stats["chunks_by_type"][ChunkType.PARAGRAPH.value] > 0
    assert stats["chunks_by_type"][ChunkType.SENTENCE.value] > 0
    assert stats["messages_with_chunks"] > 0
    
    # Clean up
    with get_session() as session:
        session.query(Chunk).filter(Chunk.message_id == message.id).delete()
        session.commit()