# carchive2/src/carchive2/agents/ollama_content_agent.py
import requests
import json
import re
from typing import Optional
from carchive.agents.base_content_agent import BaseContentAgent
from carchive.core.config import OLLAMA_URL

class OllamaContentAgent(BaseContentAgent):
    def __init__(self, model_name: str = "llama3.2"):
        self.base_url = OLLAMA_URL  # e.g., "http://localhost:11434"
        self.model_name = model_name
        self.agent_name = f"ollama-{model_name}"

    def process_task(
        self,
        task: str,
        content: str,
        context: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> str:
        # Build the prompt using the provided template or a default for the task.
        if prompt_template:
            prompt = prompt_template.format(content=content)
        else:
            if task == "summary":
                prompt = f"Summarize the following content concisely:\n\n{content}"
            elif task == "gencom":
                prompt = f"Please provide a comment on the following content:\n\n{content}"
            else:
                prompt = f"Process the following content for task '{task}':\n\n{content}"
        if context:
            prompt = context + "\n" + prompt

        # Prepare the payload for Ollama's chat endpoint.
        payload = {"model": self.model_name, "messages": [{"role": "user", "content": prompt}]}
        url = f"{self.base_url}/api/chat"
        response = requests.post(url, json=payload)
        response.raise_for_status()

        # Try to decode JSON from the response.
        try:
            data = response.json()
        except Exception as e:
            # If standard parsing fails, try to extract the first JSON object.
            raw = response.text.strip()
            # Log the raw response to help debug
            print("Raw response text:", raw)
            # Use a regular expression to extract the first JSON object.
            match = re.search(r'({.*?})\s*(?:$|\n)', raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except Exception as e2:
                    raise ValueError(f"Failed to parse JSON from extracted text: {match.group(1)}") from e2
            else:
                raise ValueError(f"Could not extract a JSON object from the response: {raw}") from e

        return data.get("completion", "")
