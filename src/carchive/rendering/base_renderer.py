# src/carchive/rendering/base_renderer.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

class ContentRenderer(ABC):
    """
    Base abstract class for all renderers, defining the common interface.
    """
    
    @abstractmethod
    def render_text(self, text: str) -> str:
        """
        Render text content to the target format.
        """
        pass
    
    @abstractmethod
    def render_collection(self, collection_name: str, output_path: str, 
                         template: str = "default", include_metadata: bool = False) -> str:
        """
        Render a collection to the target format.
        """
        pass
        
    @abstractmethod
    def render_conversation(self, conversation_id: str, output_path: str,
                           template: str = "default", include_raw: bool = False) -> str:
        """
        Render a conversation to the target format.
        """
        pass
        
    @abstractmethod
    def render_search_results(self, results: List[Dict[str, Any]], output_path: str,
                             template: str = "default") -> str:
        """
        Render search results to the target format.
        """
        pass