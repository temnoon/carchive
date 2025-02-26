"""
Anthropic implementation of multimodal agent.
"""

try:
    import anthropic
    import base64
    from pathlib import Path
except ImportError:
    anthropic = None

import requests
import base64
from pathlib import Path
from typing import List, Dict, Optional, Any

from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

class AnthropicMultimodalAgent(BaseMultimodalAgent):
    """Anthropic implementation of multimodal capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-opus-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the Anthropic multimodal agent.
        
        Args:
            api_key: Anthropic API key
            model_name: Name of the Claude model to use (should be a vision model)
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
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64-encoded image data
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _detect_media_type(self, image_path: str) -> str:
        """Detect media type based on file extension.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            MIME type for the image
        """
        ext = Path(image_path).suffix.lower()
        if ext == '.png':
            return 'image/png'
        elif ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.gif':
            return 'image/gif'
        elif ext == '.webp':
            return 'image/webp'
        else:
            return 'application/octet-stream'
    
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
        if self.client:
            # Use the official SDK if available
            messages = context or []
            
            # Create content with text and images
            content = []
            content.append({"type": "text", "text": prompt})
            
            # Add image media for each image path
            for image_path in image_paths:
                base64_image = self._encode_image(image_path)
                media_type = self._detect_media_type(image_path)
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image
                    }
                })
            
            # Add user message with content
            user_message = {"role": "user", "content": content}
            
            # Calculate final messages list
            if not messages:
                final_messages = [user_message]
            else:
                # Keep the existing context and add our new message
                final_messages = messages
                final_messages.append(user_message)
            
            response = self.client.messages.create(
                model=self._model_name,
                messages=final_messages,
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
            
            # Create content with text and images
            content = []
            content.append({"type": "text", "text": prompt})
            
            # Add image media for each image path
            for image_path in image_paths:
                base64_image = self._encode_image(image_path)
                media_type = self._detect_media_type(image_path)
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image
                    }
                })
            
            # Add user message with content
            user_message = {"role": "user", "content": content}
            
            # Calculate final messages list
            if not context:
                final_messages = [user_message]
            else:
                # Keep the existing context and add our new message
                final_messages = context
                final_messages.append(user_message)
            
            data = {
                "model": self._model_name,
                "messages": final_messages,
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