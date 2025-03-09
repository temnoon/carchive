#!/usr/bin/env python3
"""
Test script for the Groq agent implementation.
"""

import os
import sys
import time

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.carchive.agents.manager import AgentManager

def test_groq_chat_agent():
    """Test the Groq chat agent."""
    manager = AgentManager()
    
    # Get a Groq chat agent
    try:
        agent = manager.get_chat_agent("groq")
        print(f"Agent created: {agent.agent_name}")
        
        # Simple test prompt
        start_time = time.time()
        response = agent.chat("Tell me about the importance of fast language models in 3 sentences.")
        end_time = time.time()
        
        print(f"\nResponse from {agent.provider} ({agent._model_name}):")
        print(response)
        print(f"\nResponse time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

def test_groq_content_agent():
    """Test the Groq content agent."""
    manager = AgentManager()
    
    # Get a Groq content agent
    try:
        agent = manager.get_content_agent("groq")
        print(f"Agent created: {agent.agent_name}")
        
        # Test summarization
        text = """
        Vector databases are specialized database systems designed to store, manage, and search high-dimensional 
        vector embeddings efficiently. These embeddings are numerical representations of data like text, images, 
        or audio, created by machine learning models. Vector databases employ approximate nearest neighbor (ANN) 
        algorithms to find similar vectors quickly, making them essential for applications that require semantic 
        search, recommendation systems, and similarity matching. Unlike traditional databases that excel at exact 
        matches, vector databases find items that are conceptually similar. Popular vector databases include 
        Pinecone, Milvus, Weaviate, and Qdrant, with some traditional databases like PostgreSQL offering vector 
        capabilities through extensions like pgvector. These systems are crucial for modern AI applications 
        where understanding meaning and context is more important than exact keyword matching.
        """
        
        start_time = time.time()
        summary = agent.summarize(text)
        end_time = time.time()
        
        print(f"\nSummary from {agent.provider}:")
        print(summary)
        print(f"\nSummarization time: {end_time - start_time:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Testing Groq Chat Agent...")
    chat_success = test_groq_chat_agent()
    
    print("\n" + "-" * 50 + "\n")
    
    print("Testing Groq Content Agent...")
    content_success = test_groq_content_agent()
    
    if chat_success and content_success:
        print("\nAll tests passed successfully!")
    else:
        print("\nSome tests failed.")