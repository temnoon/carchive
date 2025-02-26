"""
Ollama implementation of chat agent.
"""

import requests
from typing import List, Dict, Optional, Any

from carchive.agents.base.chat_agent import BaseChatAgent

class OllamaChatAgent(BaseChatAgent):
    """Ollama implementation of chat capabilities."""
    
    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        """Initialize the Ollama chat agent.
        
        Args:
            model_name: Name of the chat model to use
            base_url: URL of the Ollama server
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        self._model_name = model_name
        self._base_url = base_url
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "ollama"
    
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
        # Prepare messages for Ollama chat API
        messages = []
        
        # Add context messages if provided
        if context:
            messages.extend(context)
        
        # If no context or prompt not in context, add the prompt
        if not context or not any(msg.get("role") == "user" and msg.get("content") == prompt for msg in messages):
            messages.append({"role": "user", "content": prompt})
        
        # Make API call
        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False  # Ensure we get a complete response, not streamed
        }
        
        url = f"{self._base_url}/api/chat"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        # Handle possible streaming response with newlines
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            # If it's a streaming response with multiple JSON objects, grab the last complete one
            lines = response.text.strip().split('\n')
            if lines and len(lines) > 0:
                try:
                    import json
                    # Try to parse the last line which should be a complete message
                    data = json.loads(lines[-1])
                except (json.JSONDecodeError, IndexError):
                    # If that fails, just extract the content directly using simple text parsing
                    content = ""
                    for line in lines:
                        if '"content":"' in line:
                            start = line.find('"content":"') + 11
                            end = line.find('"', start)
                            if start > 0 and end > start:
                                content += line[start:end]
                    return content or "Error: Could not parse response"
        
        # Ollama may have different response formats
        return data.get("completion") or data.get("response") or data.get("message", {}).get("content", "")
    
    def generate_summaries(self, texts: List[str]) -> List[str]:
        """Generate summaries for a list of texts.
        
        Args:
            texts: List of texts to summarize
            
        Returns:
            List of summary texts
        """
        # Customize prompt for Ollama models
        results = []
        for text in texts:
            prompt = f"Summarize the following text concisely:\n\n{text}"
            results.append(self.chat(prompt))
        return results