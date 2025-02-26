"""
Base class for multimodal capabilities.
"""

from abc import abstractmethod
from typing import List, Dict, Optional, Any, Union

from carchive.agents.base.chat_agent import BaseChatAgent


class BaseMultimodalAgent(BaseChatAgent):
    """Base class for multimodal capabilities."""
    
    @abstractmethod
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
        raise NotImplementedError("Multimodal functionality not implemented")
    
    def analyze_image(self, image_path: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a single image.
        
        Args:
            image_path: Path to the image file
            prompt: Optional specific prompt for analysis
                   If not provided, a default analysis prompt is used
            
        Returns:
            Analysis results as a dictionary
        """
        if prompt is None:
            prompt = "Describe this image in detail, including main subjects, colors, and composition."
        
        response = self.chat_with_images(prompt, [image_path])
        return {"analysis": response}