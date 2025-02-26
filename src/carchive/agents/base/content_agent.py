"""
Base class for content processing capabilities.
"""

from abc import abstractmethod
from typing import Dict, List, Optional, Any, Union

from carchive.agents.base.agent import BaseAgent


class BaseContentAgent(BaseAgent):
    """Base class for content processing capabilities."""
    
    @abstractmethod
    def process_task(
        self,
        task: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """Process content for a specific task.
        
        Args:
            task: The type of processing to perform (e.g., "summarize", "analyze")
            content: The text content to process
            context: Optional context information for processing
            prompt_template: Optional template for constructing prompts
                             Should contain a {content} placeholder
            
        Returns:
            Processed content as either a string or structured data
        """
        raise NotImplementedError("Content processing not implemented")
    
    def summarize(self, content: str, **kwargs) -> str:
        """Summarize the given content.
        
        Args:
            content: The text to summarize
            **kwargs: Additional arguments passed to process_task
            
        Returns:
            Summarized text
        """
        result = self.process_task("summarize", content, **kwargs)
        # Ensure we return a string, even if process_task returns a dict
        if isinstance(result, dict):
            return result.get("summary", str(result))
        return result
    
    def analyze(self, content: str, **kwargs) -> Dict[str, Any]:
        """Analyze the given content.
        
        Args:
            content: The text to analyze
            **kwargs: Additional arguments passed to process_task
            
        Returns:
            Analysis results as a dictionary
        """
        result = self.process_task("analyze", content, **kwargs)
        # Ensure we return a dict, even if process_task returns a string
        if isinstance(result, str):
            return {"analysis": result}
        return result