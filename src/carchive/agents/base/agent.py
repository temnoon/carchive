# src/carchive/agents/base/agent.py
"""
Base class for all agent implementations with common functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any


class BaseAgent(ABC):
    """Base class for all agent implementations."""
    
    def __init__(self, **kwargs):
        """Initialize agent with common configurations."""
        # Store any common configuration
        self._config = kwargs
        
    @property
    def agent_name(self) -> str:
        """Get the name of this agent."""
        return self.__class__.__name__
        
    @property
    def provider(self) -> str:
        """Get the provider name for this agent.
        
        This should be overridden by provider-specific implementations.
        """
        return "base"
        
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value safely."""
        return self._config.get(key, default)
        
    def validate_config(self, required_keys: list) -> bool:
        """Validate that all required configuration keys are present."""
        for key in required_keys:
            if key not in self._config:
                raise ValueError(f"Missing required configuration key: {key}")
        return True