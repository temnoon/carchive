# carchive2/agents/nomic_text_embed_agent.py

import requests
from typing import List, Optional
from pydantic import BaseModel
from carchive.agents.base import BaseAgent
from carchive.core.config import OLLAMA_URL, EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSIONS

# Pydantic model for validating Nomic embedding responses
class NomicEmbeddingResponse(BaseModel):
    embedding: List[float]

class NomicTextEmbedAgent(BaseAgent):
    def __init__(
        self,
        base_url: str = OLLAMA_URL,
        model_name: str = EMBEDDING_MODEL_NAME,
        dimensions: int = EMBEDDING_DIMENSIONS
    ):
        self._base_url = base_url
        self._model_name = model_name
        self._dimensions = dimensions

    def generate_embedding(self, text: str) -> List[float]:
        payload = {
            "prompt": text,
            "model": self._model_name,
            "dimensions": self._dimensions
        }
        url = f"{self._base_url}/embeddings"
        response = requests.post(url, json=payload)
        response.raise_for_status()
        # Parse and validate the response using Pydantic
        parsed = NomicEmbeddingResponse.parse_obj(response.json())
        embedding = parsed.embedding
        if len(embedding) != self._dimensions:
            # Optionally log a warning if the dimensions mismatch
            pass
        return embedding

    def chat(self, prompt: str, context: Optional[str] = None) -> str:
        return "Chat not implemented for NomicTextEmbedAgent."
