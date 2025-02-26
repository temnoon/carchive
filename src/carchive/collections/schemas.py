# carchive2/collections/schemas.py

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid

class CollectionItemSchema(BaseModel):
    message_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    meta_info: Optional[Dict[str, Any]] = None

class CollectionCreateSchema(BaseModel):
    name: str
    meta_info: Optional[Dict[str, Any]] = None
    items: Optional[List[CollectionItemSchema]] = None

class CollectionUpdateSchema(BaseModel):
    name: Optional[str]
    meta_info: Optional[Dict[str, Any]]
