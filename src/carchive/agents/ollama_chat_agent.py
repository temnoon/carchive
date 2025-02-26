# carchive2/agents/ollama_chat_agent.py

import requests
from typing import List, Optional, Dict, Any
from carchive.agents.base import BaseAgent

class OllamaChatAgent(BaseAgent):
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        from carchive.core.config import get_secure_value
        self._base_url = get_secure_value("OLLAMA_URL", base_url)
        """
        Initialize with a specific model.
        """
        self._model_name = model_name

    def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("OllamaChatAgent does not support embeddings.")

    def chat(self, prompt: str, context: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        """
        Send a chat request to the Ollama server using the specified model.

        :param prompt: The user prompt.
        :param context: Optional system/context message.
        :param images: Optional list of image file paths or base64-encoded data.
        :return: The assistant's response as a string.
        """
        messages: List[Dict[str, Any]] = []
        if context:
            messages.append({"role": "system", "content": context})
        user_message: Dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            user_message["images"] = images
        messages.append(user_message)

        payload = {"model": self._model_name, "messages": messages}
        url = f"{self._base_url}/api/chat"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        # Adjust key access based on actual API response structure
        return data.get("completion") or data.get("response") or ""
