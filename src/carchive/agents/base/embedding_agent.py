"""
Base class for embedding generation capabilities.
"""

from abc import abstractmethod
from typing import List, Dict, Optional

from carchive.agents.base.agent import BaseAgent


class BaseEmbeddingAgent(BaseAgent):
    """Base class for embedding generation capabilities."""
    
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for the given text.
        
        Args:
            text: The input text to embed
            
        Returns:
            A list of floats representing the embedding vector
        """
        raise NotImplementedError("Embedding generation not implemented")
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate multiple embeddings for a list of texts.
        
        Default implementation calls generate_embedding for each text,
        but providers may override with batch processing.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        return [self.generate_embedding(text) for text in texts]