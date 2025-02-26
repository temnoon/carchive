"""
Base class for chat capabilities.
"""

from abc import abstractmethod
from typing import List, Dict, Optional, Any, Union

from carchive.agents.base.agent import BaseAgent


class BaseChatAgent(BaseAgent):
    """Base class for chat capabilities."""
    
    @abstractmethod
    def chat(self, prompt: str, context: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate a chat response for the given prompt.
        
        Args:
            prompt: The user's input prompt
            context: Optional conversation history or context
                     Format: [{"role": "user", "content": "..."}, 
                             {"role": "assistant", "content": "..."}]
            
        Returns:
            Generated response text
        """
        raise NotImplementedError("Chat functionality not implemented")
    
    def generate_summaries(self, texts: List[str]) -> List[str]:
        """Generate summaries for a list of texts.
        
        Default implementation generates a summary prompt for each text.
        
        Args:
            texts: List of texts to summarize
            
        Returns:
            List of summary texts
        """
        results = []
        for text in texts:
            prompt = f"Please summarize the following text concisely: {text}"
            results.append(self.chat(prompt))
        return results