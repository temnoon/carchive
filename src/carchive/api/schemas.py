"""
Pydantic schemas for API data validation and serialization.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class MediaBase(BaseModel):
    """Base schema for media files."""
    id: UUID
    file_path: str
    media_type: str
    original_file_id: Optional[str] = None
    file_name: Optional[str] = None
    is_generated: bool = False
    created_at: datetime

    class Config:
        """Pydantic configuration."""
        orm_mode = True


class MessageBase(BaseModel):
    """Base schema for messages."""
    id: UUID
    conversation_id: UUID
    content: Optional[str] = None
    created_at: datetime
    meta_info: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class MessageDetail(MessageBase):
    """Detailed message schema with media."""
    media: Optional[MediaBase] = None
    referenced_media: Optional[List[MediaBase]] = []
    media_items: Optional[List[MediaBase]] = []


class ConversationBase(BaseModel):
    """Base schema for conversations."""
    id: UUID
    title: Optional[str] = None
    created_at: datetime
    meta_info: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class ConversationDetail(ConversationBase):
    """Detailed conversation schema with messages."""
    messages: List[MessageDetail] = []
    message_count: int = 0


class MediaDetail(MediaBase):
    """Detailed media schema with message references."""
    message: Optional[MessageBase] = None
    linked_message: Optional[MessageBase] = None


class CollectionItemBase(BaseModel):
    """Base schema for collection items."""
    message_id: Optional[UUID] = None
    chunk_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    meta_info: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class CollectionBase(BaseModel):
    """Base schema for collections."""
    id: UUID
    name: str
    created_at: datetime
    meta_info: Optional[Dict[str, Any]] = None
    
    class Config:
        """Pydantic configuration."""
        orm_mode = True


class CollectionCreate(BaseModel):
    """Schema for creating a new collection."""
    name: str
    meta_info: Optional[Dict[str, Any]] = None
    items: Optional[List[CollectionItemBase]] = None


class CollectionUpdate(BaseModel):
    """Schema for updating an existing collection."""
    name: Optional[str] = None
    meta_info: Optional[Dict[str, Any]] = None


class CollectionDetail(CollectionBase):
    """Detailed collection schema with items."""
    items: List[Dict[str, Any]] = []
    item_count: int = 0


class SearchResult(BaseModel):
    """Schema for search results."""
    conversations: List[ConversationBase] = []
    messages: List[MessageBase] = []
    media: List[MediaBase] = []
    total_conversations: int = 0
    total_messages: int = 0
    total_media: int = 0


class APIError(BaseModel):
    """Schema for API errors."""
    error: str
    code: int
    details: Optional[Dict[str, Any]] = None