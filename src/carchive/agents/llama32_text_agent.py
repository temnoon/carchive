# carchive2/agents/llama32_text_agent.py
import requests
from typing import Optional, Dict, Any, List
from carchive.agents.base import BaseAgent
from carchive.core.config import OLLAMA_URL

class Llama32TextAgent(BaseAgent):
    """
    An agent that uses the local Llama 3.2 3B model for text-based completions,
    summaries, quality assessments, and other general chat tasks.
    """
    def __init__(self, base_url: str = OLLAMA_URL, model_name: str = "llama3.2-3b"):
        self._base_url = base_url
        self._model_name = model_name

    def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError("This agent is only for text-based classification/chat.")

    def chat(self, prompt: str, context: Optional[str] = None, images: Optional[List[str]] = None) -> str:
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        user_msg: Dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            user_msg["images"] = images
        messages.append(user_msg)

        payload = {"model": self._model_name, "messages": messages}
        url = f"{self._base_url}/api/chat"
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("completion", "")
