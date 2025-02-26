"""
Anthropic implementation of chat agent.
"""

try:
    import anthropic
except ImportError:
    anthropic = None

import requests
from typing import List, Dict, Optional, Any

from carchive.agents.base.chat_agent import BaseChatAgent

class AnthropicChatAgent(BaseChatAgent):
    """Anthropic implementation of chat capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the Anthropic chat agent.
        
        Args:
            api_key: Anthropic API key
            model_name: Name of the Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        self._api_key = api_key
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._temperature = temperature
        
        # Initialize client if anthropic package is available
        self.client = None
        if anthropic:
            self.client = anthropic.Anthropic(api_key=api_key)
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "anthropic"
    
    def chat(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a chat response for the given prompt.
        
        Args:
            prompt: The user's input prompt
            context: Optional conversation history or context
                    Format: [{"role": "user", "content": "..."}, 
                            {"role": "assistant", "content": "..."}]
            
        Returns:
            Generated response text
        """
        if self.client:
            # Use the official SDK if available
            messages = context or []
            
            # Add the prompt message if not already in context
            if not any(msg.get("role") == "user" and msg.get("content") == prompt for msg in messages):
                messages.append({"role": "user", "content": prompt})
            
            response = self.client.messages.create(
                model=self._model_name,
                messages=messages,
                max_tokens=self._max_tokens,
                temperature=self._temperature
            )
            
            return response.content[0].text
        else:
            # Fallback to direct API calls
            headers = {
                "x-api-key": self._api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # Format messages for API
            formatted_messages = []
            if context:
                formatted_messages.extend(context)
            
            # Add the prompt message if not already in context
            if not any(msg.get("role") == "user" and msg.get("content") == prompt for msg in formatted_messages):
                formatted_messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": self._model_name,
                "messages": formatted_messages,
                "max_tokens": self._max_tokens,
                "temperature": self._temperature
            }
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                json=data,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("content", [{"text": ""}])[0]["text"]