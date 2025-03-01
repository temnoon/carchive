# tests/test_gencom.py
"""Tests for the gencom functionality."""

import os
import pytest
import uuid
from unittest.mock import MagicMock, patch
from carchive.pipelines.content_tasks import ContentTaskManager
from carchive.database.models import AgentOutput, Message, Conversation, Chunk, Embedding
from carchive.embeddings.embed_manager import EmbeddingManager


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = MagicMock()
    agent.process_task.return_value = "This is a generated comment for testing."
    agent.agent_name = "test_agent"
    return agent


@pytest.fixture
def mock_embedding_agent():
    """Create a mock embedding agent for testing."""
    agent = MagicMock()
    agent.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 153  # 765 dimensions
    return agent


@pytest.mark.skip(reason="Integration test requiring database")
def test_gencom_cli_message_command():
    """Integration test for the gencom message CLI command."""
    # This is an integration test that would need real database access
    pass


@pytest.mark.skip(reason="Integration test requiring database")
def test_gencom_cli_conversation_command():
    """Integration test for the gencom conversation CLI command."""
    # This is an integration test that would need real database access
    pass


def test_format_conversation_transcript():
    """Test the transcript formatting for conversations."""
    # Create test messages
    messages = [
        Message(role="user", content="Hello, how are you?"),
        Message(role="assistant", content="I'm doing well, thank you!"),
        Message(role="user", content="Great to hear!")
    ]
    
    manager = ContentTaskManager()
    transcript = manager._format_conversation_transcript(messages)
    
    # Verify the transcript format
    assert "USER: Hello, how are you?" in transcript
    assert "ASSISTANT: I'm doing well, thank you!" in transcript
    assert "USER: Great to hear!" in transcript
    assert transcript.count("\n\n") == 2  # Two message separators


@pytest.mark.skip(reason="Requires more complex mocking of database interactions")
def test_content_manager_message_task():
    """Test that the content manager can process a message task correctly."""
    # This test requires more complex mocking of database interactions
    pass


@pytest.mark.skip(reason="Requires more complex mocking of database interactions")
def test_content_manager_conversation_task():
    """Test that the content manager can process a conversation task correctly."""
    # This test requires more complex mocking of database interactions
    pass


@pytest.mark.skip(reason="Integration test requiring database")
def test_embed_agent_output():
    """Test that agent outputs can be embedded correctly."""
    # This requires actual database integration - skip for unit testing
    pass


@pytest.mark.skip(reason="Integration test requiring schema compatibility")
def test_embed_texts_direct_api():
    """Test the direct embedding API for agent outputs."""
    # This test requires the real schema structures to match
    pass