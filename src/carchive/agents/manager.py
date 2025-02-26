# carchive/src/carchive/agents/manager.py

from typing import Optional, Dict, Type, Any, Union

from carchive.core.config import (
    OLLAMA_URL,
    EMBEDDING_PROVIDER,
    CHAT_PROVIDER,
    CONTENT_PROVIDER,
    MULTIMODAL_PROVIDER,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIMENSIONS,
    VISION_MODEL_NAME,
    TEXT_MODEL_NAME
)
from carchive.agents.base.agent import BaseAgent
from carchive.agents.base.embedding_agent import BaseEmbeddingAgent
from carchive.agents.base.chat_agent import BaseChatAgent
from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

# Provider imports
from carchive.agents.providers.openai.embedding_agent import OpenAIEmbeddingAgent
from carchive.agents.providers.openai.chat_agent import OpenAIChatAgent
from carchive.agents.providers.openai.content_agent import OpenAIContentAgent
from carchive.agents.providers.openai.multimodal_agent import OpenAIMultimodalAgent

from carchive.agents.providers.ollama.embedding_agent import OllamaEmbeddingAgent
from carchive.agents.providers.ollama.chat_agent import OllamaChatAgent
from carchive.agents.providers.ollama.content_agent import OllamaContentAgent
from carchive.agents.providers.ollama.multimodal_agent import OllamaMultimodalAgent

from carchive.agents.providers.anthropic.chat_agent import AnthropicChatAgent
from carchive.agents.providers.anthropic.multimodal_agent import AnthropicMultimodalAgent

class AgentManager:
    """
    Factory class for creating agent instances based on type and provider.
    """
    def __init__(self):
        """Initialize agent manager with configuration."""
        from carchive.core.config import OPENAI_API_KEY, ANTHROPIC_API_KEY
        self.openai_key = OPENAI_API_KEY or "sk-..."
        self.anthropic_key = ANTHROPIC_API_KEY or "sk-ant-..."
        self.ollama_url = OLLAMA_URL  # Defaults to "http://localhost:11434"
        
        # Provider configurations
        self.provider_config = {
            "openai": {
                "api_key": self.openai_key,
                "embedding_model": "text-embedding-ada-002",
                "chat_model": "gpt-3.5-turbo",
                "vision_model": "gpt-4-vision-preview",
            },
            "ollama": {
                "base_url": self.ollama_url,
                "embedding_model": EMBEDDING_MODEL_NAME,
                "dimensions": EMBEDDING_DIMENSIONS,
                "chat_model": TEXT_MODEL_NAME,
                "vision_model": VISION_MODEL_NAME,
            },
            "anthropic": {
                "api_key": self.anthropic_key,
                "chat_model": "claude-3-sonnet-20240229",
                "vision_model": "claude-3-opus-20240229",
            }
        }
        
        # Agent class mappings
        self.agent_classes = {
            "embedding": {
                "openai": OpenAIEmbeddingAgent,
                "ollama": OllamaEmbeddingAgent,
            },
            "chat": {
                "openai": OpenAIChatAgent,
                "ollama": OllamaChatAgent,
                "anthropic": AnthropicChatAgent,
            },
            "content": {
                "openai": OpenAIContentAgent,
                "ollama": OllamaContentAgent,
            },
            "multimodal": {
                "openai": OpenAIMultimodalAgent,
                "ollama": OllamaMultimodalAgent,
                "anthropic": AnthropicMultimodalAgent,
            }
        }
    
    def get_embedding_agent(self, provider: Optional[str] = None) -> BaseEmbeddingAgent:
        """
        Get an embedding agent for the specified provider.
        
        Args:
            provider: Provider name (e.g., "openai", "ollama")
                     If None, uses the default provider from config
                     
        Returns:
            An instance of BaseEmbeddingAgent
        """
        provider = provider or EMBEDDING_PROVIDER
        
        if provider not in self.agent_classes["embedding"]:
            raise ValueError(f"Embedding agent not available for provider: {provider}")
        
        agent_class = self.agent_classes["embedding"][provider]
        config = self.provider_config[provider]
        
        if provider == "openai":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["embedding_model"]
            )
        elif provider == "ollama":
            return agent_class(
                model_name=config["embedding_model"],
                base_url=config["base_url"],
                dimensions=config["dimensions"]
            )
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
    
    def get_chat_agent(self, provider: Optional[str] = None) -> BaseChatAgent:
        """
        Get a chat agent for the specified provider.
        
        Args:
            provider: Provider name (e.g., "openai", "ollama", "anthropic")
                     If None, uses default from config (typically "ollama")
                     
        Returns:
            An instance of BaseChatAgent
        """
        provider = provider or CHAT_PROVIDER
        
        if provider not in self.agent_classes["chat"]:
            raise ValueError(f"Chat agent not available for provider: {provider}")
        
        agent_class = self.agent_classes["chat"][provider]
        config = self.provider_config[provider]
        
        if provider == "openai":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["chat_model"]
            )
        elif provider == "ollama":
            return agent_class(
                model_name=config["chat_model"],
                base_url=config["base_url"]
            )
        elif provider == "anthropic":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["chat_model"]
            )
        else:
            raise ValueError(f"Unsupported chat provider: {provider}")
    
    def get_content_agent(self, provider: Optional[str] = None) -> BaseContentAgent:
        """
        Get a content agent for the specified provider.
        
        Args:
            provider: Provider name (e.g., "openai", "ollama")
                     If None, uses default from config (typically "ollama")
                     
        Returns:
            An instance of BaseContentAgent
        """
        provider = provider or CONTENT_PROVIDER
        
        if provider not in self.agent_classes["content"]:
            raise ValueError(f"Content agent not available for provider: {provider}")
        
        agent_class = self.agent_classes["content"][provider]
        config = self.provider_config[provider]
        
        if provider == "openai":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["chat_model"]
            )
        elif provider == "ollama":
            return agent_class(
                model_name=config["chat_model"],
                base_url=config["base_url"]
            )
        else:
            raise ValueError(f"Unsupported content provider: {provider}")
    
    def get_multimodal_agent(self, provider: Optional[str] = None) -> BaseMultimodalAgent:
        """
        Get a multimodal agent for the specified provider.
        
        Args:
            provider: Provider name (e.g., "openai", "ollama", "anthropic")
                     If None, uses default from config (typically "ollama")
                     
        Returns:
            An instance of BaseMultimodalAgent
        """
        provider = provider or MULTIMODAL_PROVIDER
        
        if provider not in self.agent_classes["multimodal"]:
            raise ValueError(f"Multimodal agent not available for provider: {provider}")
        
        agent_class = self.agent_classes["multimodal"][provider]
        config = self.provider_config[provider]
        
        if provider == "openai":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["vision_model"]
            )
        elif provider == "ollama":
            return agent_class(
                model_name=config["vision_model"],
                base_url=config["base_url"]
            )
        elif provider == "anthropic":
            return agent_class(
                api_key=config["api_key"],
                model_name=config["vision_model"]
            )
        else:
            raise ValueError(f"Unsupported multimodal provider: {provider}")
    
    def get_agent(self, provider: str) -> BaseAgent:
        """
        Legacy method for backward compatibility.
        
        Args:
            provider: Provider name with format "provider-type"
                    (e.g., "openai", "ollama-vision", "ollama-text")
                     
        Returns:
            An appropriate agent instance
        """
        if provider == "openai":
            return self.get_embedding_agent("openai")
        elif provider == "ollama-nomic":
            return self.get_embedding_agent("ollama")
        elif provider == "ollama-vision":
            return self.get_multimodal_agent("ollama")
        elif provider == "ollama-text":
            return self.get_chat_agent("ollama")
        elif provider == "ollama":
            return self.get_embedding_agent("ollama")
        else:
            raise ValueError(f"Unknown provider: {provider}")
            
    def available_providers(self, agent_type: str) -> list:
        """
        Get a list of available providers for a given agent type.
        
        Args:
            agent_type: The type of agent ("embedding", "chat", "content", "multimodal")
            
        Returns:
            List of provider names
        """
        if agent_type not in self.agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        return list(self.agent_classes[agent_type].keys())