"""
OpenAI implementation of multimodal agent.
"""

try:
    import openai
    import base64
    from pathlib import Path
except ImportError:
    openai = None  # Handle the absence gracefully

from typing import List, Dict, Optional, Any
import base64
from pathlib import Path

from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

class OpenAIMultimodalAgent(BaseMultimodalAgent):
    """OpenAI implementation of multimodal capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4-vision-preview",
        temperature: float = 0.7,
        max_tokens: int = 300,
        **kwargs
    ):
        """Initialize the OpenAI multimodal agent.
        
        Args:
            api_key: OpenAI API key
            model_name: Name of the vision model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        if openai is None:
            raise ImportError("The 'openai' library is not installed. Please install it to use OpenAIMultimodalAgent.")
        
        self._api_key = api_key
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens
        openai.api_key = self._api_key
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "openai"
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64-encoded image data
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def chat(
        self,
        prompt: str,
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Standard chat without images.
        
        Args:
            prompt: The user's input prompt
            context: Optional conversation history or context
            
        Returns:
            Generated response text
        """
        messages = context or []
        
        # If context doesn't contain our prompt, add it
        if not any(msg.get("role") == "user" and msg.get("content") == prompt for msg in messages):
            messages.append({"role": "user", "content": prompt})
        
        response = openai.ChatCompletion.create(
            model=self._model_name,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens
        )
        
        return response.choices[0].message.content
    
    def chat_with_images(
        self,
        prompt: str,
        image_paths: List[str],
        context: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Generate a chat response for the given prompt and images.
        
        Args:
            prompt: The user's input prompt
            image_paths: List of paths to image files
            context: Optional conversation history or context
            
        Returns:
            Generated response text
        """
        # Prepare base messages from context
        messages = context or []
        
        # Create content with text and images
        content = [{"type": "text", "text": prompt}]
        
        # Add each image to content
        for image_path in image_paths:
            base64_image = self._encode_image(image_path)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        # Add user message with combined content
        messages.append({"role": "user", "content": content})
        
        # Make API call
        response = openai.ChatCompletion.create(
            model=self._model_name,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens
        )
        
        return response.choices[0].message.content