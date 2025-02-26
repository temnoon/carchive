# src/carchive/agents/ollama_agent.py
"""
Example agent implementation for a local Ollama server.
Adjust to match the version and endpoints of your Ollama setup.
"""

import requests
from typing import List, Optional
from carchive.agents.base import BaseAgent
from carchive.core.config import EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME, OLLAMA_URL

class OllamaAgent(BaseAgent):
    def __init__(self, model_name: str, model_version: str, base_url: Optional[str] = None):
        """
        :param model_name: Model name used for embeddings.
        :param model_version: Model version used for embeddings.
        :param base_url: Optional base URL for Ollama server.
        """
        self.model_name = model_name
        self.model_version = model_version
        self.base_url = base_url or "http://localhost:11434"

    def generate_embedding(self, text: str, dimensions: Optional[int] = None) -> List[float]:
        """
        Generate an embedding using the Ollama embedding endpoint.

        :param text: The input text to embed.
        :param dimensions: Optional size of the embedding vector.
        :return: A list of floats representing the embedding vector.
        """
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model_version,
            "prompt": text,
            "dimensions": dimensions if dimensions is not None else 768
        }
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("embedding", [])

    def chat(self, prompt: str, context: Optional[str] = None, model_name: Optional[str] = None) -> str:
        """
        Initiate a chat completion using the Ollama server.
        Optionally specify a different model for chat completions.
        """
        model = model_name if model_name else self.model_version

        if context:
            combined_prompt = f"{context}\n\nUser: {prompt}\nAssistant:"
        else:
            combined_prompt = f"User: {prompt}\nAssistant:"

        payload = {"prompt": combined_prompt, "model": model}
        url = f"{self.base_url}/generate"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("completion", "")
