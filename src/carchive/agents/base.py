"""
Defines an abstract BaseAgent for LLM-based tasks (embeddings, chat).
"""

from abc import ABC, abstractmethod
from typing import List, Optional

class BaseAgent(ABC):

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def chat(self, prompt: str, context: Optional[str] = None) -> str:
        pass
