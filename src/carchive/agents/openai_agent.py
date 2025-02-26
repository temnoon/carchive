# carchive2/src/carchive2/agents/openai_agent.py

"""
Example implementation of BaseAgent for OpenAI with Pydantic validation.
"""

try:
    import openai
except ImportError:
    openai = None  # Handle the absence gracefully

from typing import List, Optional
from pydantic import BaseModel
from carchive.agents.base import BaseAgent

# Pydantic models for validating OpenAI responses
class OpenAIEmbeddingData(BaseModel):
    embedding: List[float]

class OpenAIEmbeddingResponse(BaseModel):
    data: List[OpenAIEmbeddingData]

class OpenAIChatMessage(BaseModel):
    role: str
    content: str

class OpenAIChatChoice(BaseModel):
    message: OpenAIChatMessage

class OpenAIChatResponse(BaseModel):
    choices: List[OpenAIChatChoice]

class OpenAIAgent(BaseAgent):
    def __init__(
        self,
        api_key: str,
        model_embedding: str = "text-embedding-ada-002",
        model_chat: str = "gpt-3.5-turbo"
    ):
        if openai is None:
            raise ImportError("The 'openai' library is not installed. Please install it to use OpenAIAgent.")
        self._api_key = api_key
        self._model_embedding = model_embedding
        self._model_chat = model_chat
        openai.api_key = self._api_key

    def generate_embedding(self, text: str) -> List[float]:
        response = openai.Embedding.create(model=self._model_embedding, input=text)
        # Validate and parse the response using Pydantic
        parsed = OpenAIEmbeddingResponse.parse_obj(response)
        return parsed.data[0].embedding

    def chat(self, prompt: str, context: Optional[str] = None) -> str:
        if openai is None:
            raise ImportError("The 'openai' library is not installed. Please install it to use OpenAIAgent.")
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        response = openai.ChatCompletion.create(
            model=self._model_chat,
            messages=messages,
            temperature=0.7
        )
        # Validate and parse the chat response using Pydantic
        parsed = OpenAIChatResponse.parse_obj(response)
        return parsed.choices[0].message.content
