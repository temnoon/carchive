"""
Ollama implementation of multimodal agent.
"""

import requests
import base64
from pathlib import Path
from typing import List, Dict, Optional, Any

from carchive.agents.base.multimodal_agent import BaseMultimodalAgent

class OllamaMultimodalAgent(BaseMultimodalAgent):
    """Ollama implementation of multimodal capabilities."""
    
    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        """Initialize the Ollama multimodal agent.
        
        Args:
            model_name: Name of the multimodal model to use (e.g., "llava")
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
        # Prepare messages for Ollama chat API
        messages = []
        
        # Add context messages if provided
        if context:
            messages.extend(context)
        
        # Add the prompt message if not already in context
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
        # Prepare messages
        messages = []
        
        # Add context messages if provided
        if context:
            messages.extend(context)
        
        # Encode images
        images = [self._encode_image(image_path) for image_path in image_paths]
        
        # Add user message with images
        messages.append({
            "role": "user",
            "content": prompt,
            "images": images
        })
        
        # Make API call
        payload = {
            "model": self._model_name,
            "messages": messages,
            "stream": False  # Ensure we get a complete response, not streamed
        }
        
        url = f"{self._base_url}/api/chat"
        
        try:
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
            
        except requests.exceptions.HTTPError as e:
            # Handle multimodal-specific errors
            if e.response.status_code == 500:
                # Check if the model is loaded
                status_resp = requests.get(f"{self._base_url}/api/version")
                if status_resp.status_code == 200:
                    return f"Error: The model {self._model_name} may not support multimodal/image inputs, or the image format is unsupported."
                else:
                    return f"Error: The Ollama server is not responding correctly."
            raise e