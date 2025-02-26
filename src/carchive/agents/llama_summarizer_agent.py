# carchive2/agents/llama_summarizer_agent.py

import asyncio
import aiohttp
import logging
from typing import Optional, List
from carchive.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class LlamaSummarizerAgent(BaseAgent):
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/summarize"  # Ensure this endpoint exists
        self.agent_name = "llama3.2"  # Define the agent name

    async def generate_summary_async(self, session: aiohttp.ClientSession, text: str) -> Optional[str]:
        """
        Asynchronously sends text to the Llama3.2 model for summarization.

        :param session: The aiohttp session.
        :param text: The text to summarize.
        :return: The summary string or None if failed.
        """
        payload = {
            "model": self.model_name,
            "text": text
        }
        try:
            async with session.post(self.endpoint, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                summary = data.get("summary")
                if summary:
                    logger.debug(f"Generated summary for text: {text[:30]}...")
                    return summary
                else:
                    logger.error("No summary returned from the model.")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {e}")
            return None
        except ValueError:
            logger.error("Invalid JSON response.")
            return None

    async def generate_summaries_async(self, texts: List[str]) -> List[Optional[str]]:
        """
        Asynchronously generates summaries for a list of texts.

        :param texts: The texts to summarize.
        :return: A list of summary strings or None if failed.
        """
        summaries = []
        async with aiohttp.ClientSession() as session:
            tasks = [self.generate_summary_async(session, text) for text in texts]
            summaries = await asyncio.gather(*tasks)
        return summaries

    def generate_summaries(self, texts: List[str]) -> List[Optional[str]]:
        """
        Synchronously generates summaries by running the asynchronous method.

        :param texts: The texts to summarize.
        :return: A list of summary strings or None if failed.
        """
        return asyncio.run(self.generate_summaries_async(texts))
