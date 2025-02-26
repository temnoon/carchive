"""
OpenAI implementation of embedding agent.
"""

try:
    import openai
except ImportError:
    openai = None  # Handle the absence gracefully

from typing import List, Dict, Any
from pydantic import BaseModel

from carchive.agents.base.embedding_agent import BaseEmbeddingAgent

# Pydantic models for validating OpenAI responses
class OpenAIEmbeddingData(BaseModel):
    embedding: List[float]
    index: int
    object: str

class OpenAIEmbeddingResponse(BaseModel):
    data: List[OpenAIEmbeddingData]
    model: str
    object: str
    usage: Dict[str, int]

class OpenAIEmbeddingAgent(BaseEmbeddingAgent):
    """OpenAI implementation of embedding capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-ada-002",
        **kwargs
    ):
        """Initialize the OpenAI embedding agent.
        
        Args:
            api_key: OpenAI API key
            model_name: Name of the embedding model to use
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        if openai is None:
            raise ImportError("The 'openai' library is not installed. Please install it to use OpenAIEmbeddingAgent.")
        
        self._api_key = api_key
        self._model_name = model_name
        openai.api_key = self._api_key
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "openai"
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text.
        
        Args:
            text: The input text to embed
            
        Returns:
            A list of floats representing the embedding vector
        """
        response = openai.Embedding.create(
            model=self._model_name,
            input=text
        )
        
        # Validate and parse the response using Pydantic
        parsed = OpenAIEmbeddingResponse.parse_obj(response)
        return parsed.data[0].embedding
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate multiple embeddings in a batch request.
        
        This overrides the default implementation to use OpenAI's batch API.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
            
        response = openai.Embedding.create(
            model=self._model_name,
            input=texts
        )
        
        # Validate and parse the response using Pydantic
        parsed = OpenAIEmbeddingResponse.parse_obj(response)
        
        # Sort by index to ensure we return in the same order as input
        embedding_data = sorted(parsed.data, key=lambda x: x.index)
        return [data.embedding for data in embedding_data]