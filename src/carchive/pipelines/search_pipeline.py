# carchive2/pipelines/search_pipeline.py
from typing import Any, List, Protocol

class PipelineStep(Protocol):
    def run(self, data: Any) -> Any:
        ...

class SearchPipeline:
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    def run(self, initial_data: Any) -> Any:
        data = initial_data
        for step in self.steps:
            data = step.run(data)
        return data
