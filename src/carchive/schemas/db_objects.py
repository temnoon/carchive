"""
Pydantic schemas for database objects.
This file is a minimal placeholder to avoid import errors until the real API is ready.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# Base model for all database objects
class DBObject(BaseModel):
    """Base schema for all database objects."""
    id: UUID
    created_at: datetime
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class ConversationBase(DBObject):
    """Base schema for conversations."""
    title: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class ConversationRead(ConversationBase):
    """Schema for reading conversations."""
    pass


class MessageBase(DBObject):
    """Base schema for messages."""
    conversation_id: UUID
    content: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class MessageRead(MessageBase):
    """Schema for reading messages."""
    pass


class MessageWithConversationRead(MessageRead):
    """Schema for reading messages with their associated conversation."""
    conversation: ConversationRead


class MediaBase(DBObject):
    """Base schema for media."""
    file_path: str
    media_type: str


class MediaRead(MediaBase):
    """Schema for reading media."""
    pass


class ChunkBase(DBObject):
    """Base schema for text chunks."""
    text: str
    embedding: Optional[List[float]] = None
    message_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class ChunkRead(ChunkBase):
    """Schema for reading chunks."""
    pass


class CollectionBase(DBObject):
    """Base schema for collections."""
    name: str
    description: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class CollectionRead(CollectionBase):
    """Schema for reading collections."""
    pass