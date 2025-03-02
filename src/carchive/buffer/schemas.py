"""
Schemas for the results buffer system.

This module defines the data models for temporary and persistent results buffers
that store search results and other collections of entities for multi-step workflows.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

from carchive.schemas.db_objects import DBObject


class BufferType(str, Enum):
    """Types of buffers with different persistence characteristics."""
    EPHEMERAL = "ephemeral"     # In-memory only, lost when session ends
    SESSION = "session"         # Persists during CLI session
    PERSISTENT = "persistent"   # Saved to database, persists across sessions


class BufferItemSchema(BaseModel):
    """Schema for items to be added to a buffer."""
    message_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    gencom_id: Optional[uuid.UUID] = None
    position: Optional[int] = None  # For maintaining order
    meta_info: Optional[Dict[str, Any]] = None


class BufferCreateSchema(BaseModel):
    """Schema for creating a new buffer."""
    name: str
    buffer_type: BufferType = BufferType.SESSION
    session_id: Optional[str] = None  # For session-scoped buffers
    description: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None
    items: Optional[List[BufferItemSchema]] = None


class BufferUpdateSchema(BaseModel):
    """Schema for updating an existing buffer."""
    name: Optional[str] = None
    description: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class BufferOperationType(str, Enum):
    """Types of operations that can be performed on buffers."""
    FILTER = "filter"           # Filter items by criteria
    MERGE = "merge"             # Combine multiple buffers
    SORT = "sort"               # Sort buffer items
    TRANSFORM = "transform"     # Transform items (e.g., extract fields)
    PAGINATE = "paginate"       # Get a subset of items
    INTERSECT = "intersect"     # Set intersection of buffers
    UNION = "union"             # Set union of buffers
    DIFFERENCE = "difference"   # Set difference of buffers


class BufferFilterCriteria(BaseModel):
    """Criteria for filtering buffer contents."""
    role: Optional[str] = None          # Filter by message role
    content: Optional[str] = None       # Text content to match
    days: Optional[int] = None          # Filter by age in days
    has_image: Optional[bool] = None    # Filter by presence of images
    exclude_ids: Optional[List[uuid.UUID]] = None  # IDs to exclude


class BufferRead(BaseModel):
    """Schema for buffer metadata with item count."""
    id: uuid.UUID
    name: str
    buffer_type: BufferType
    session_id: Optional[str] = None
    description: Optional[str] = None
    item_count: int
    created_at: datetime
    updated_at: datetime
    meta_info: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True


class BufferDetailedRead(BufferRead):
    """Schema for buffer with full item details."""
    items: List[DBObject] = Field(default_factory=list)