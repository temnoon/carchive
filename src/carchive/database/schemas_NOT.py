"""
Pydantic schemas for input/output validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any
import uuid
from datetime import datetime

class ConversationBase(BaseModel):
    title: Optional[str] = None
    meta_info: Optional[Any] = None

class ConversationCreate(ConversationBase):
    pass

class ConversationRead(ConversationBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

# Similarly, define MessageBase, MessageCreate, etc.
# You can replicate these patterns for each table as needed.
