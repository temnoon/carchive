"""
Ollama implementation of embedding agent.
"""

import requests
from typing import List, Optional, Dict, Any

from carchive.agents.base.embedding_agent import BaseEmbeddingAgent

class OllamaEmbeddingAgent(BaseEmbeddingAgent):
    """Ollama implementation of embedding capabilities."""
    
    def __init__(
        self,
        model_name: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        dimensions: Optional[int] = None,
        **kwargs
    ):
        """Initialize the Ollama embedding agent.
        
        Args:
            model_name: Name of the embedding model to use
            base_url: URL of the Ollama server
            dimensions: Optional size of the embedding vector
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        self._model_name = model_name
        self._base_url = base_url
        self._dimensions = dimensions or 768
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "ollama"
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The input text to embed
            
        Returns:
            A list of floats representing the embedding vector
        """
        url = f"{self._base_url}/api/embeddings"
        payload = {
            "model": self._model_name,
            "prompt": text,
            "dimensions": self._dimensions
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        return data.get("embedding", [])
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate multiple embeddings.
        
        Note: Ollama doesn't support batch embedding directly,
        so we call the API for each text.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        return [self.generate_embedding(text) for text in texts]