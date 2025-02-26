"""
Ollama implementation of content agent.
"""

import requests
import json
import re
from typing import Dict, List, Optional, Any, Union

from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.providers.ollama.chat_agent import OllamaChatAgent

class OllamaContentAgent(BaseContentAgent):
    """Ollama implementation of content processing capabilities."""
    
    def __init__(
        self,
        model_name: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        **kwargs
    ):
        """Initialize the Ollama content agent.
        
        Args:
            model_name: Name of the model to use
            base_url: URL of the Ollama server
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        # Use the Ollama chat agent for actual interactions
        self._chat_agent = OllamaChatAgent(
            model_name=model_name,
            base_url=base_url
        )
        self._model_name = model_name
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "ollama"
    
    @property
    def agent_name(self) -> str:
        """Get the name of this agent with model info."""
        return f"ollama-{self._model_name}"
    
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
        # Build the prompt using the provided template or a default for the task
        if prompt_template:
            prompt = prompt_template.format(content=content)
        else:
            if task == "summarize" or task == "summary":
                prompt = f"Summarize the following content concisely:\n\n{content}"
            elif task == "analyze":
                prompt = (
                    f"Analyze the following text and return the results as a JSON object "
                    f"with keys for 'main_topics', 'sentiment', and 'key_points':\n\n{content}"
                )
            elif task == "gencom":
                prompt = f"Please provide a comment on the following content:\n\n{content}"
            else:
                prompt = f"Process the following content for task '{task}':\n\n{content}"
        
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