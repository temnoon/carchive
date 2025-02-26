# carchive2/src/carchive2/agents/ollama_content_agent.py
import requests
import json
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
        # Build the prompt using the provided template or defaults.
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

        # Prepare the payload.
        # Note: Including "stream": False asks Ollama to return the full response as one JSON object.
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        url = f"{self.base_url}/api/chat"
        response = requests.post(url, json=payload)
        response.raise_for_status()

        # Parse the response as JSON.
        try:
            data = response.json()
        except Exception as e:
            # If parsing fails, log and re-raise.
            raise ValueError(f"Failed to parse JSON response: {response.text}") from e

        # We now assume that the entire response is contained in one JSON packet.
        # For example, data might look like:
        # {
        #     "model": "llama3.2",
        #     "created_at": "2025-02-01T04:36:39.709651Z",
        #     "message": {"role": "assistant", "content": "Full completion text here..."},
        #     "done": true,
        #     ...
        # }
        return data.get("completion", "")
