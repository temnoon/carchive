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
        return ChunkRead.from_orm(obj)
    else:
        raise ValueError(f"Unsupported object type: {type(obj)}")
