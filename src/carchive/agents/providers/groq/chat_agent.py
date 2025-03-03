"""
Groq implementation of chat agent.
"""

try:
    import groq
except ImportError:
    groq = None  # Handle the absence gracefully

from typing import List, Dict, Optional, Any
from pydantic import BaseModel

from carchive.agents.base.chat_agent import BaseChatAgent

# Pydantic models for validating Groq responses
class GroqChatMessage(BaseModel):
    role: str
    content: str

class GroqChatChoice(BaseModel):
    message: GroqChatMessage
    index: int
    finish_reason: str

class GroqChatResponse(BaseModel):
    choices: List[GroqChatChoice]
    id: str
    model: str
    object: str
    usage: Dict[str, int]

class GroqChatAgent(BaseChatAgent):
    """Groq implementation of chat capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.2-3b-preview",
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the Groq chat agent.
        
        Args:
            api_key: Groq API key
            model_name: Name of the chat model to use
            temperature: Temperature parameter for generation (0.0 to 1.0)
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        if groq is None:
            raise ImportError("The 'groq' library is not installed. Please install it to use GroqChatAgent.")
        
        self._api_key = api_key
        self._model_name = model_name
        self._temperature = temperature
        self._client = groq.Groq(api_key=self._api_key)
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "groq"
    
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
        # Prepare messages for Groq chat
        messages = context or []
        
        # If context doesn't contain our prompt, add it
        if not any(msg.get("role") == "user" and msg.get("content") == prompt for msg in messages):
            messages.append({"role": "user", "content": prompt})
        
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=self._temperature
        )
        
        # Validate and parse the response using Pydantic
        parsed = GroqChatResponse.parse_obj(response)
        return parsed.choices[0].message.content