"""
Agents package for the carchive project.
"""

# Base classes
from carchive.agents.base.agent import BaseAgent
from carchive.agents.base.embedding_agent import BaseEmbeddingAgent
from carchive.agents.base.chat_agent import BaseChatAgent
from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

# Manager
from carchive.agents.manager import AgentManager

# Factory function for convenient access
def get_agent(agent_type: str, provider: str = None):
    """
    Get an agent instance of the specified type and provider.
    
    Args:
        agent_type: Type of agent ("embedding", "chat", "content", "multimodal")
        provider: Provider name (e.g., "openai", "ollama", "anthropic")
                 If None, uses the default provider for that agent type
    
    Returns:
        An agent instance of the appropriate type
    
    Examples:
        >>> from carchive.agents import get_agent
        >>> chat_agent = get_agent("chat", "openai")
        >>> embedding_agent = get_agent("embedding", "ollama")
    """
    manager = AgentManager()
    
    if agent_type == "embedding":
        return manager.get_embedding_agent(provider)
    elif agent_type == "chat":
        return manager.get_chat_agent(provider)
    elif agent_type == "content":
        return manager.get_content_agent(provider)
    elif agent_type == "multimodal":
        return manager.get_multimodal_agent(provider)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

# Legacy support function
def get_legacy_agent(provider: str):
    """Get an agent using the legacy provider format."""
    return AgentManager().get_agent(provider)