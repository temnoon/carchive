# carchive2/utils/conversions.py
from carchive.schemas.db_objects import (
    ConversationRead, MessageRead, CollectionRead, ChunkRead, DBObject
)
from carchive.database.models import Conversation, Message, Collection, Chunk

def convert_to_pydantic(obj) -> DBObject:
    if isinstance(obj, Conversation):
        return ConversationRead.from_orm(obj)
    elif isinstance(obj, Message):
        return MessageRead.from_orm(obj)
    elif isinstance(obj, Collection):
        return CollectionRead.from_orm(obj)
    elif isinstance(obj, Chunk):
        # Fix for Chunk: map content to text and meta_info to metadata
        from carchive.schemas.db_objects import ChunkRead
        from datetime import datetime
        
        # Get created_at from message if available, otherwise use current time
        created_time = None
        if obj.message and hasattr(obj.message, 'created_at'):
            created_time = obj.message.created_at
        else:
            created_time = datetime.now()
            
        chunk_data = {
            "id": obj.id,
            "created_at": created_time,
            "text": obj.content or "",
            "message_id": obj.message_id,
            "metadata": obj.meta_info or {}
        }
        return ChunkRead(**chunk_data)
    else:
        raise ValueError(f"Unsupported object type: {type(obj)}")
