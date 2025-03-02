"""
Test the buffer to collection conversion functionality.

This test verifies that the buffer_to_collection command works correctly,
especially with the fix for handling AgentOutputRead objects.
"""

import pytest
import uuid
from datetime import datetime

from carchive.buffer.buffer_manager import BufferManager
from carchive.buffer.schemas import BufferCreateSchema, BufferItemSchema, BufferType
from carchive.collections.collection_manager import CollectionManager
from carchive.schemas.db_objects import MessageRead, ConversationRead, ChunkRead, DBObject
from carchive.database.session import get_session
from carchive.database.models import Message, Conversation, Chunk, AgentOutput, Collection, CollectionItem, ResultsBuffer, BufferItem

# Define AgentOutputRead class consistent with how it's defined in buffer_manager.py
class AgentOutputRead(DBObject):
    """Read schema for agent outputs (gencom results)."""
    content: str
    output_type: str
    target_type: str
    target_id: uuid.UUID
    agent_name: str


class TestBufferToCollection:
    """Test suite for buffer to collection functionality."""

    def setup_method(self):
        """Set up test data."""
        # Generate some test IDs
        self.message_id = uuid.uuid4()
        self.conversation_id = uuid.uuid4()
        self.chunk_id = uuid.uuid4()
        self.gencom_id = uuid.uuid4()
        
        # Create test entities in the database
        with get_session() as session:
            # Create a test message
            message = Message(
                id=self.message_id,
                conversation_id=self.conversation_id,
                content="Test message content",
                role="user",
                parent_id=None,
                created_at=datetime.now(),
                meta_info={"conversation_id": str(self.conversation_id)}
            )
            session.add(message)
            
            # Create a test conversation
            conversation = Conversation(
                id=self.conversation_id,
                title="Test conversation",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                meta_info={"source": "test"}
            )
            session.add(conversation)
            
            # Create a test chunk 
            chunk = Chunk(
                id=self.chunk_id,
                content="Test chunk content",
                message_id=self.message_id
            )
            session.add(chunk)
            
            # Create a test agent output (gencom)
            agent_output = AgentOutput(
                id=self.gencom_id,
                content="Test agent output",
                output_type="text",
                target_type="message",
                target_id=self.message_id,
                agent_name="test_agent"
            )
            session.add(agent_output)
            
            session.commit()
            
        # Create a test buffer with unique name
        unique_name = f"test_buffer_{uuid.uuid4().hex[:8]}"
        buffer_data = BufferCreateSchema(
            name=unique_name,
            buffer_type=BufferType.SESSION,
            description="Test buffer for conversion to collection"
        )
        self.buffer = BufferManager.create_buffer(buffer_data)
        
        # Add items to the buffer
        items = [
            BufferItemSchema(message_id=self.message_id),
            BufferItemSchema(conversation_id=self.conversation_id),
            BufferItemSchema(chunk_id=self.chunk_id),
            BufferItemSchema(gencom_id=self.gencom_id)
        ]
        BufferManager.add_items_to_buffer(self.buffer.id, items)

    def teardown_method(self):
        """Clean up test data."""
        with get_session() as session:
            try:
                # Delete the test buffer
                session.query(BufferItem).filter_by(buffer_id=self.buffer.id).delete()
                session.query(ResultsBuffer).filter_by(id=self.buffer.id).delete()
            except Exception as e:
                print(f"Error cleaning up buffer: {e}")
            
            # Delete any created collections
            try:
                collections = session.query(Collection).filter(Collection.name.like("test_collection_%")).all()
                for collection in collections:
                    session.query(CollectionItem).filter_by(collection_id=collection.id).delete()
                    session.delete(collection)
            except Exception as e:
                print(f"Error cleaning up collections: {e}")
            
            # Delete test entities
            try:
                session.query(AgentOutput).filter_by(id=self.gencom_id).delete()
                session.query(Chunk).filter_by(id=self.chunk_id).delete()
                session.query(Message).filter_by(id=self.message_id).delete()
                session.query(Conversation).filter_by(id=self.conversation_id).delete()
            except Exception as e:
                print(f"Error cleaning up entities: {e}")
            
            try:
                session.commit()
            except Exception as e:
                print(f"Error committing cleanup: {e}")
                session.rollback()

    def test_buffer_to_collection(self):
        """Test converting a buffer to a collection."""
        # First verify that the buffer contains all the expected items
        buffer_contents = BufferManager.get_buffer_contents_as_dbobjects(self.buffer.id)
        
        # Verify the buffer contains all types of objects, including AgentOutputRead
        buffer_types = [type(obj).__name__ for obj in buffer_contents]
        assert 'MessageRead' in buffer_types, "Buffer should contain a MessageRead object"
        assert 'ConversationRead' in buffer_types, "Buffer should contain a ConversationRead object"
        assert 'ChunkRead' in buffer_types, "Buffer should contain a ChunkRead object"
        assert any(hasattr(obj, 'target_type') for obj in buffer_contents), "Buffer should contain an AgentOutput object"
        
        # Find the agent output object
        agent_output_obj = next((obj for obj in buffer_contents if hasattr(obj, 'target_type')), None)
        assert agent_output_obj is not None, "Agent output object not found in buffer"
        assert agent_output_obj.target_id == self.message_id, "Agent output target should be the test message"
        
        # Convert buffer to collection with unique name
        collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
        collection_id = BufferManager.convert_buffer_to_collection(
            self.buffer.id, 
            collection_name,
            "Test collection created from buffer"
        )
        
        # Verify the collection was created
        with get_session() as session:
            collection = session.query(Collection).filter_by(id=collection_id).first()
            assert collection is not None, "Collection should be created"
            assert collection.name == collection_name, "Collection should have the correct name"
            assert "Test collection created from buffer" in str(collection.meta_info), "Collection should have the correct description"
            
            # Check that items were added to the collection
            items = session.query(CollectionItem).filter_by(collection_id=collection_id).all()
            
            # Count by type to verify all types were handled correctly
            message_items = sum(1 for item in items if item.message_id == self.message_id)
            conversation_items = sum(1 for item in items if item.conversation_id == self.conversation_id)
            chunk_items = sum(1 for item in items if item.chunk_id == self.chunk_id)
            
            # The message can appear twice - once from direct inclusion and once from
            # being a target of the agent output, depending on implementation
            assert message_items >= 1, "Message should be included at least once"
            # The conversation can appear more than once if it's also referenced elsewhere
            assert conversation_items >= 1, "Conversation should be included at least once"
            # The chunk should appear at least once
            assert chunk_items >= 1, "Chunk should be included at least once"
            
            # The AgentOutput should have been converted to its target (the message),
            # We expect 3-4 items (message [possibly twice], conversation, chunk)
            assert 3 <= len(items) <= 4, "Collection should have 3-4 items total"
            
            # Verify the collection items are correctly linked to their sources
            for item in items:
                if item.message_id:
                    message = session.query(Message).filter_by(id=item.message_id).first()
                    assert message is not None, "Message referenced in collection should exist"
                elif item.conversation_id:
                    convo = session.query(Conversation).filter_by(id=item.conversation_id).first()
                    assert convo is not None, "Conversation referenced in collection should exist"
                elif item.chunk_id:
                    chunk = session.query(Chunk).filter_by(id=item.chunk_id).first()
                    assert chunk is not None, "Chunk referenced in collection should exist"


if __name__ == "__main__":
    # Enable this to run as a standalone script
    pytest.main(["-xvs", __file__])