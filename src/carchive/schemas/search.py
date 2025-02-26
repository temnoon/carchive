"""
Pydantic schemas for search functionality.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class SearchCriteria(BaseModel):
    """Search criteria for messages and conversations."""
    query: str
    conversation_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 10
    offset: int = 0
    filters: Optional[Dict[str, Any]] = None


class SearchResult(BaseModel):
    """Search result containing conversations and messages."""
    conversations: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    total_conversations: int = 0
    total_messages: int = 0


class VectorSearchCriteria(SearchCriteria):
    """Search criteria for vector search."""
    embedding_model: Optional[str] = None
    threshold: float = 0.5
    max_distance: float = 1.0