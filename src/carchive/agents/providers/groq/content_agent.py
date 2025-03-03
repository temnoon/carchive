"""
Groq implementation of content agent.
"""

try:
    import groq
    import json
except ImportError:
    groq = None  # Handle the absence gracefully

from typing import Dict, List, Optional, Any, Union
import json

from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.providers.groq.chat_agent import GroqChatAgent

class GroqContentAgent(BaseContentAgent):
    """Groq implementation of content processing capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "llama-3.2-3b-preview",
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the Groq content agent.
        
        Args:
            api_key: Groq API key
            model_name: Name of the model to use
            temperature: Temperature for generation
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        # Use the Groq chat agent for actual interactions
        self._chat_agent = GroqChatAgent(
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "groq"
    
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
        # Use provided template or select a default based on task
        if prompt_template:
            prompt = prompt_template.format(content=content)
        else:
            if task == "summarize":
                prompt = f"Please provide a concise summary of the following text:\n\n{content}"
            elif task == "analyze":
                prompt = (
                    f"Please analyze the following text and return the results as a JSON object "
                    f"with keys for 'main_topics', 'sentiment', and 'key_points':\n\n{content}"
                )
            else:
                prompt = f"Please process the following text for the task '{task}':\n\n{content}"
        
        # Add system context if provided
        system_context = None
        if context and "system_prompt" in context:
            system_context = [{"role": "system", "content": context["system_prompt"]}]
        
        # Get response from chat agent
        response = self._chat_agent.chat(prompt, context=system_context)
        
        # If analysis task, try to parse JSON
        if task == "analyze":
            try:
                # Look for JSON in the response (in case model adds explanation text)
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                # If JSON parsing fails, return as text
                pass
        
        return response