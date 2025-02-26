"""
Test script for the refactored agent system.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from carchive.agents import get_agent
from carchive.agents.manager import AgentManager

def test_agent_types():
    """Test different agent types."""
    # Use default provider (ollama)
    embedding_agent = get_agent("embedding")
    print(f"Created embedding agent: {embedding_agent.agent_name}, provider: {embedding_agent.provider}")
    
    chat_agent = get_agent("chat")
    print(f"Created chat agent: {chat_agent.agent_name}, provider: {chat_agent.provider}")
    
    content_agent = get_agent("content")
    print(f"Created content agent: {content_agent.agent_name}, provider: {content_agent.provider}")
    
    multimodal_agent = get_agent("multimodal")
    print(f"Created multimodal agent: {multimodal_agent.agent_name}, provider: {multimodal_agent.provider}")
    
    # Get all available providers for chat
    manager = AgentManager()
    chat_providers = manager.available_providers("chat")
    print(f"Available chat providers: {chat_providers}")

def test_embedding():
    """Test embedding generation."""
    embedding_agent = get_agent("embedding")
    text = "This is a test of the embedding functionality."
    vector = embedding_agent.generate_embedding(text)
    print(f"Generated embedding with {len(vector)} dimensions")
    print(f"First 5 values: {vector[:5]}")

def main():
    print("Testing agent types...")
    test_agent_types()
    print("\nTesting embedding functionality...")
    test_embedding()

if __name__ == "__main__":
    main()