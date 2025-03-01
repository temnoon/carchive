# carchive2/embeddings/schemas.py

from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

class EmbedAllOptions(BaseModel):
    min_word_count: int = Field(default=5, description="Minimum number of words required to embed a message.")
    include_roles: Optional[List[str]] = Field(
        default=None,
        description="List of roles to include (e.g., ['user', 'assistant']). If None, includes all."
    )
    exclude_empty: bool = Field(default=True, description="Exclude messages with empty content.")

class EmbeddingTargetSchema(BaseModel):
    text: Optional[str] = None
    message_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    agent_output_id: Optional[uuid.UUID] = None

class EmbeddingRequestSchema(BaseModel):
    provider: str
    model_version: str
    store_in_db: bool = True
    targets: List[EmbeddingTargetSchema]

class EmbeddingResultSchema(BaseModel):
    db_id: uuid.UUID
    vector: List[float]
    stored: bool = True
