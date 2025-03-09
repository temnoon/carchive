"""
Anthropic implementation of content agent.
"""

import json
from typing import Dict, List, Optional, Any, Union

from carchive.agents.base.content_agent import BaseContentAgent
from carchive.agents.providers.anthropic.chat_agent import AnthropicChatAgent

class AnthropicContentAgent(BaseContentAgent):
    """Anthropic implementation of content processing capabilities."""
    
    def __init__(
        self,
        api_key: str,
        model_name: str = "claude-3-sonnet-20240229",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ):
        """Initialize the Anthropic content agent.
        
        Args:
            api_key: Anthropic API key
            model_name: Name of the Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional configuration options
        """
        super().__init__(**kwargs)
        
        # Use the Anthropic chat agent for actual interactions
        self._chat_agent = AnthropicChatAgent(
            api_key=api_key,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature
        )
        self._model_name = model_name
    
    @property
    def provider(self) -> str:
        """Get the provider name for this agent."""
        return "anthropic"
    
    @property
    def agent_name(self) -> str:
        """Get the name of this agent with model info."""
        return f"anthropic-{self._model_name}"
    
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
            elif task == "gencom_category":
                prompt = f"Analyze the following content and provide ONE specific thematic category that best describes it. Be precise and specific with your category name. Focus on the subject matter, not the format:\n\n{content}"
            elif task == "gencom_summary":
                prompt = f"Provide a concise summary (1-2 sentences) of the following content:\n\n{content}"
            elif task == "gencom_quality":
                prompt = f"Rate the quality of the following content on a scale of 1-10 and explain your rating briefly:\n\n{content}"
            elif task.startswith("gencom_"):
                # Extract the suffix and use it in the prompt
                suffix = task.replace("gencom_", "")
                prompt = f"Analyze the following content for {suffix}:\n\n{content}"
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