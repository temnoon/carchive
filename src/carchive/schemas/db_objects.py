"""
Pydantic schemas for database objects.

Notable features:
1. Conversations can have original timestamps in two formats:
   - Explicit 'create_time' and 'update_time' fields in meta_info (as Unix timestamps)
   - Encoded in the first 8 characters of 'source_conversation_id' as a hexadecimal Unix timestamp
   
This encoding pattern was discovered by observing that the first 8 characters of 
source_conversation_id (e.g., "678296b6-1138-8005-9a88-7eaa8b2bee97") represent a
hexadecimal Unix timestamp that corresponds to the conversation creation time.
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
    _first_message_time: Optional[datetime] = None
    _last_message_time: Optional[datetime] = None
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True
        underscore_attrs_are_private = False
    
    @property
    def original_create_time(self) -> Optional[datetime]:
        """
        Get the original creation time in priority order:
        1. Explicit meta_info['create_time'] from JSON
        2. First message time from the conversation
        3. Creation time in the database (fallback)
        """
        # First priority: explicit create_time in meta_info
        if self.meta_info and 'create_time' in self.meta_info:
            try:
                if timestamp_str := self.meta_info.get('create_time'):
                    timestamp = float(timestamp_str)
                    return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
        
        # Second priority: first message time
        if self._first_message_time:
            return self._first_message_time
        
        # Last resort: database created_at timestamp
        return self.created_at
    
    @property
    def original_update_time(self) -> Optional[datetime]:
        """
        Get the original update time in priority order:
        1. Explicit meta_info['update_time'] from JSON
        2. Last message time from the conversation
        3. Fall back to creation time
        """
        # First priority: explicit update_time in meta_info
        if self.meta_info and 'update_time' in self.meta_info:
            try:
                if timestamp_str := self.meta_info.get('update_time'):
                    timestamp = float(timestamp_str)
                    return datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
        
        # Second priority: last message time
        if self._last_message_time:
            return self._last_message_time
        
        # Last resort: fall back to creation time
        return self.original_create_time


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