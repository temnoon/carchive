# carchive2/agents/base_content_agent.py
from abc import ABC, abstractmethod
from typing import Optional

class BaseContentAgent(ABC):
    @abstractmethod
    def process_task(
        self,
        task: str,
        content: str,
        context: Optional[str] = None,
        prompt_template: Optional[str] = None
    ) -> str:
        """
        Process the given content for the specified task.
        Optionally use a custom prompt template (with a {content} placeholder).
        """
        pass
