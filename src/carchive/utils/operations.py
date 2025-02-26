# carchive2/utils/operations.py
from functools import singledispatch
from carchive.schemas.db_objects import (
    ConversationRead, MessageRead, CollectionRead, ChunkRead, DBObject
)

@singledispatch
def process_db_object(obj: DBObject):
    raise NotImplementedError(f"Operation not implemented for type {type(obj)}")

@process_db_object.register
def _(obj: ConversationRead):
    # Example operation for Conversation
    print(f"Processing Conversation: {obj.title}")

@process_db_object.register
def _(obj: MessageRead):
    # Example operation for Message
    print(f"Processing Message: {obj.content[:30]}...")

@process_db_object.register
def _(obj: CollectionRead):
    # Example operation for Collection
    print(f"Processing Collection: {obj.name}")

@process_db_object.register
def _(obj: ChunkRead):
    # Example operation for Chunk
    print(f"Processing Chunk at position {obj.position}")
