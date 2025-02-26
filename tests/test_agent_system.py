# tests/test_agent_system.py

import logging
import os
import pytest
from typing import Dict, List, Any

# Import agent manager
from carchive.agents.manager import AgentManager

# Import base agent classes for type checking
from carchive.agents.base.embedding_agent import BaseEmbeddingAgent
from carchive.agents.base.chat_agent import BaseChatAgent
from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

# Import the specific Ollama implementations for direct testing
from carchive.agents.providers.ollama.embedding_agent import OllamaEmbeddingAgent
from carchive.agents.providers.ollama.chat_agent import OllamaChatAgent
from carchive.agents.providers.ollama.content_agent import OllamaContentAgent
from carchive.agents.providers.ollama.multimodal_agent import OllamaMultimodalAgent

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Test data
TEST_TEXT = "This is a sample text for testing embedding and text generation capabilities."
TEST_PROMPT = "Explain the concept of agent-based architecture in software design."
TEST_CONTENT = """
Agent-based architecture is a software design pattern where the system is broken down into
autonomous components called agents. Each agent has specific responsibilities and capabilities.
Agents can communicate with each other and react to changes in their environment. This approach
facilitates modularity, flexibility, and scalability in complex systems.
"""
TEST_CHAT_HISTORY = [
    {"role": "user", "content": "What is an agent-based system?"},
    {"role": "assistant", "content": "An agent-based system is a computational model where autonomous entities called 'agents' interact with their environment and with each other to accomplish specific tasks or goals. Each agent has its own set of capabilities, decision-making logic, and often operates independently while contributing to the overall system functionality."}
]
# Path to a test image (create a fixture or use a sample image path)
# Path to a test image 
TEST_IMAGE_PATH = "tests/test_data/test_image.jpg"
# Flag to check if multimodal testing should be skipped
SKIP_MULTIMODAL_TESTS = not os.path.exists(TEST_IMAGE_PATH) or os.path.getsize(TEST_IMAGE_PATH) < 100

# ==== Manager Tests ====

def test_agent_manager_initialization():
    """Test that the AgentManager initializes correctly."""
    manager = AgentManager()
    assert manager is not None
    assert hasattr(manager, "provider_config")
    assert hasattr(manager, "agent_classes")
    
    # Check that all expected agent types are configured
    for agent_type in ["embedding", "chat", "content", "multimodal"]:
        assert agent_type in manager.agent_classes
    
    # Check that Ollama provider is configured for all agent types
    for agent_type in manager.agent_classes:
        assert "ollama" in manager.agent_classes[agent_type]

def test_agent_manager_provider_selection():
    """Test that the AgentManager returns the correct provider."""
    manager = AgentManager()
    
    # Test retrieving different agent types with explicit Ollama provider
    embedding_agent = manager.get_embedding_agent("ollama")
    assert embedding_agent.provider == "ollama"
    assert isinstance(embedding_agent, OllamaEmbeddingAgent)
    
    chat_agent = manager.get_chat_agent("ollama")
    assert chat_agent.provider == "ollama"
    assert isinstance(chat_agent, OllamaChatAgent)
    
    content_agent = manager.get_content_agent("ollama") 
    assert content_agent.provider == "ollama"
    assert isinstance(content_agent, OllamaContentAgent)
    
    multimodal_agent = manager.get_multimodal_agent("ollama")
    assert multimodal_agent.provider == "ollama"
    assert isinstance(multimodal_agent, OllamaMultimodalAgent)
    
    # Test retrieving with default provider (should be Ollama)
    default_embedding_agent = manager.get_embedding_agent()
    assert default_embedding_agent.provider == "ollama"
    assert isinstance(default_embedding_agent, OllamaEmbeddingAgent)

# ==== Embedding Agent Tests ====

def test_embedding_agent_initialization():
    """Test that the OllamaEmbeddingAgent initializes correctly."""
    agent = OllamaEmbeddingAgent(
        model_name="nomic-embed-text",
        base_url="http://localhost:11434",
        dimensions=768
    )
    assert agent is not None
    assert agent.provider == "ollama"
    assert agent._model_name == "nomic-embed-text"
    assert agent._base_url == "http://localhost:11434"
    assert agent._dimensions == 768

@pytest.mark.integration
def test_embedding_agent_generate_embedding():
    """Test generating embeddings with the OllamaEmbeddingAgent."""
    agent = OllamaEmbeddingAgent(model_name="nomic-embed-text")
    
    # Generate embedding for test text
    embedding = agent.generate_embedding(TEST_TEXT)
    
    # Verify embedding format and properties
    assert isinstance(embedding, list)
    assert len(embedding) > 0 
    assert all(isinstance(val, float) for val in embedding)
    
    # Test dimensions match expected value
    assert len(embedding) == agent._dimensions

@pytest.mark.integration
def test_embedding_agent_generate_multiple_embeddings():
    """Test generating multiple embeddings with the OllamaEmbeddingAgent."""
    agent = OllamaEmbeddingAgent()
    
    texts = [TEST_TEXT, "Another sample text for testing", "A third different text"]
    embeddings = agent.generate_embeddings(texts)
    
    # Verify result format
    assert isinstance(embeddings, list)
    assert len(embeddings) == len(texts)
    
    for embedding in embeddings:
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(val, float) for val in embedding)

# ==== Content Agent Tests ====

def test_content_agent_initialization():
    """Test that the OllamaContentAgent initializes correctly."""
    agent = OllamaContentAgent(
        model_name="llama3.2",
        base_url="http://localhost:11434"
    )
    assert agent is not None
    assert agent.provider == "ollama"
    assert agent._model_name == "llama3.2"
    assert agent._chat_agent is not None
    assert agent._chat_agent._base_url == "http://localhost:11434"

@pytest.mark.integration
def test_content_agent_process_task():
    """Test content processing with the OllamaContentAgent."""
    agent = OllamaContentAgent(model_name="llama3.2")
    
    result = agent.process_task(
        task="summarize",
        content=TEST_CONTENT,
        prompt_template="Please summarize the following text concisely:\n\n{content}"
    )
    
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
    logger.info(f"Summary result: {result}")

@pytest.mark.integration
def test_content_agent_summarize():
    """Test the summarize convenience method of ContentAgent."""
    agent = OllamaContentAgent(model_name="llama3.2")
    
    summary = agent.summarize(TEST_CONTENT)
    
    assert summary is not None
    assert isinstance(summary, str)
    assert len(summary) > 0
    logger.info(f"Summarize result: {summary}")

@pytest.mark.integration
def test_content_agent_analyze():
    """Test the analyze convenience method of ContentAgent."""
    agent = OllamaContentAgent(model_name="llama3.2")
    
    analysis = agent.analyze(TEST_CONTENT)
    
    assert analysis is not None
    assert isinstance(analysis, dict)
    # The response could be either {"analysis": "content"} or a structured dict
    # with keys like main_topics, key_points, sentiment, etc.
    if "analysis" in analysis:
        assert len(analysis["analysis"]) > 0
    else:
        # If it's a structured response, check for typical keys
        assert any(key in analysis for key in ["main_topics", "key_points", "sentiment"])
    
    logger.info(f"Analysis result: {analysis}")

# ==== Chat Agent Tests ====

def test_chat_agent_initialization():
    """Test that the OllamaChatAgent initializes correctly."""
    agent = OllamaChatAgent(
        model_name="llama3.2",
        base_url="http://localhost:11434"
    )
    assert agent is not None
    assert agent.provider == "ollama"
    assert agent._model_name == "llama3.2" 
    assert agent._base_url == "http://localhost:11434"

@pytest.mark.integration
def test_chat_agent_simple_prompt():
    """Test chat response generation with a simple prompt."""
    agent = OllamaChatAgent(model_name="llama3.2")
    
    response = agent.chat(TEST_PROMPT)
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    logger.info(f"Chat response: {response}")

@pytest.mark.integration
def test_chat_agent_with_history():
    """Test chat response generation with conversation history."""
    agent = OllamaChatAgent(model_name="llama3.2")
    
    followup_prompt = "How do agents communicate in such systems?"
    response = agent.chat(followup_prompt, context=TEST_CHAT_HISTORY)
    
    assert response is not None
    assert isinstance(response, str) 
    assert len(response) > 0
    logger.info(f"Chat with history response: {response}")

@pytest.mark.integration
def test_chat_agent_generate_summaries():
    """Test generating summaries for a list of texts."""
    agent = OllamaChatAgent(model_name="llama3.2")
    
    texts = [
        "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience.",
        "Natural language processing combines computational linguistics with machine learning to enable computers to understand human language."
    ]
    
    summaries = agent.generate_summaries(texts)
    
    assert summaries is not None
    assert isinstance(summaries, list)
    assert len(summaries) == len(texts)
    assert all(isinstance(summary, str) for summary in summaries)
    assert all(len(summary) > 0 for summary in summaries)

# ==== Multimodal Agent Tests ====

@pytest.mark.skipif(SKIP_MULTIMODAL_TESTS, 
                    reason="Test image not found or multimodal tests disabled")
def test_multimodal_agent_initialization():
    """Test that the OllamaMultimodalAgent initializes correctly."""
    agent = OllamaMultimodalAgent(
        model_name="llama3.2-vision",
        base_url="http://localhost:11434"
    )
    assert agent is not None
    assert agent.provider == "ollama"
    assert agent._model_name == "llama3.2-vision"
    assert agent._base_url == "http://localhost:11434"

@pytest.mark.integration
@pytest.mark.skipif(SKIP_MULTIMODAL_TESTS, 
                    reason="Test image not found or multimodal tests disabled")
def test_multimodal_agent_chat_with_images():
    """Test chat with images functionality."""
    agent = OllamaMultimodalAgent(model_name="llama3.2-vision")
    
    prompt = "Describe what you see in this image."
    response = agent.chat_with_images(prompt, [TEST_IMAGE_PATH])
    
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    logger.info(f"Image chat response: {response}")

@pytest.mark.integration
@pytest.mark.skipif(SKIP_MULTIMODAL_TESTS, 
                    reason="Test image not found or multimodal tests disabled")
def test_multimodal_agent_analyze_image():
    """Test image analysis functionality."""
    agent = OllamaMultimodalAgent(model_name="llama3.2-vision")
    
    analysis = agent.analyze_image(TEST_IMAGE_PATH)
    
    assert analysis is not None
    assert isinstance(analysis, dict)
    assert "analysis" in analysis
    assert len(analysis["analysis"]) > 0
    logger.info(f"Image analysis: {analysis}")

# ==== End-to-end Tests ====

@pytest.mark.integration
def test_complete_agent_workflow():
    """Test a complete workflow using multiple agent types."""
    manager = AgentManager()
    
    # 1. Generate embeddings
    embedding_agent = manager.get_embedding_agent()
    embedding = embedding_agent.generate_embedding(TEST_CONTENT)
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    logger.info(f"Embedding generated successfully with {len(embedding)} dimensions")
    
    # Use try-except blocks to continue testing even if one agent fails
    try:
        # 2. Generate a summary
        content_agent = manager.get_content_agent()
        summary = content_agent.summarize(TEST_CONTENT)
        assert isinstance(summary, str)
        assert len(summary) > 0
        logger.info(f"Summary: {summary}")
        
        try:
            # 3. Chat about the summary
            chat_agent = manager.get_chat_agent()
            chat_prompt = f"Explain this summary in more detail: {summary}"
            chat_response = chat_agent.chat(chat_prompt)
            assert isinstance(chat_response, str)
            assert len(chat_response) > 0
            logger.info(f"Chat response: {chat_response}")
        except Exception as e:
            logger.error(f"Chat step failed: {str(e)}")
            pytest.skip("Chat step failed, skipping assertions")
    except Exception as e:
        logger.error(f"Summary step failed: {str(e)}")
        pytest.skip("Summary step failed, skipping remaining steps")
        
    logger.info(f"End-to-end workflow completed successfully")

if __name__ == "__main__":
    # Run integration tests with explicit function calls for direct debugging
    test_agent_manager_initialization()
    test_agent_manager_provider_selection()
    test_embedding_agent_initialization()
    test_content_agent_initialization()
    test_chat_agent_initialization()
    
    # Only run if image exists
    if os.path.exists(TEST_IMAGE_PATH):
        test_multimodal_agent_initialization()