# carchive2/collections/collection_manager.py

from typing import List, Optional
import uuid
from carchive.database.session import get_session
from carchive.database.models import Collection, CollectionItem, Message, Conversation, Chunk
from carchive.collections.schemas import CollectionCreateSchema, CollectionUpdateSchema
from carchive.schemas.db_objects import (
    ConversationRead, MessageRead, CollectionRead, ChunkRead, DBObject
)
class CollectionManager:
    @staticmethod
    def create_collection(input_data: CollectionCreateSchema) -> Collection:
        with get_session() as session:
            # Create the collection
            new_coll = Collection(
                name=input_data.name,
                meta_info=input_data.meta_info or {}
            )
            session.add(new_coll)
            session.flush()

            # If items are provided, link them
            if input_data.items:
                for item in input_data.items:
                    citem = CollectionItem(
                        collection_id=new_coll.id,
                        message_id=item.message_id,
                        chunk_id=item.chunk_id,
                        conversation_id=item.conversation_id,
                        meta_info=item.meta_info or {}
                    )
                    session.add(citem)

            session.commit()
            session.refresh(new_coll)
            return new_coll

    @staticmethod
    def create_collection_from_search(
            name: str,
            search_criteria: 'AdvancedSearchCriteria',
            meta_info: Optional[dict] = None
        ) -> Collection:
            """
            Runs an advanced search, then creates a new collection of all results.
            If results contain both conversations and messages, we store them accordingly.
            """
            from carchive.search.search_manager import SearchManager

            objects = SearchManager.advanced_search(search_criteria)  # DBObject items
            return CollectionManager.create_collection_from_dbobjects(name, objects, meta_info)


    @staticmethod
    def update_collection(coll_id: str, update_data: CollectionUpdateSchema) -> Collection:
        with get_session() as session:
            coll = session.query(Collection).filter_by(id=coll_id).first()
            if not coll:
                raise ValueError(f"Collection {coll_id} not found.")

            if update_data.name is not None:
                coll.name = update_data.name
            if update_data.meta_info is not None:
                coll.meta_info.update(update_data.meta_info)

            session.commit()
            session.refresh(coll)
            return coll

    @staticmethod
    def add_items(coll_id: str, items: List['CollectionItemSchema']) -> bool:
        """Add items to an existing collection."""
        with get_session() as session:
            collection = session.query(Collection).filter_by(id=coll_id).first()
            if not collection:
                raise ValueError(f"Collection {coll_id} not found.")
                
            # Create and add new collection items
            for item in items:
                citem = CollectionItem(
                    collection_id=collection.id,
                    message_id=item.message_id,
                    chunk_id=item.chunk_id,
                    conversation_id=item.conversation_id,
                    meta_info=item.meta_info or {}
                )
                session.add(citem)
                
            session.commit()
            return True
            
    @staticmethod
    def remove_item(coll_id: str, item_id: str) -> bool:
        """Remove an item from a collection by item ID."""
        with get_session() as session:
            collection = session.query(Collection).filter_by(id=coll_id).first()
            if not collection:
                raise ValueError(f"Collection {coll_id} not found.")
                
            item = session.query(CollectionItem).filter_by(id=item_id, collection_id=coll_id).first()
            if not item:
                raise ValueError(f"Item {item_id} not found in collection {coll_id}.")
                
            session.delete(item)
            session.commit()
            return True
            
    @staticmethod
    def delete_collection(coll_id: str) -> bool:
        """Delete a collection and all its items."""
        with get_session() as session:
            collection = session.query(Collection).filter_by(id=coll_id).first()
            if not collection:
                raise ValueError(f"Collection {coll_id} not found.")
                
            # Delete all items first (should cascade, but being explicit)
            session.query(CollectionItem).filter_by(collection_id=coll_id).delete()
                
            # Delete the collection
            session.delete(collection)
            session.commit()
            return True

    @staticmethod
    def get_collection(coll_id: str) -> Optional[Collection]:
        with get_session() as session:
            return session.query(Collection).filter_by(id=coll_id).first()

    @staticmethod
    def list_collections() -> List[Collection]:
        with get_session() as session:
            return session.query(Collection).all()

    @staticmethod
    def create_collection_from_dbobjects(name: str, objects: List[DBObject], meta_info: Optional[dict] = None) -> Collection:
        """
        Create a collection from a list of heterogeneous DBObjects.
        """
        items = []
        for obj in objects:
            if isinstance(obj, ConversationRead):
                item = {"conversation_id": obj.id}
            elif isinstance(obj, MessageRead):
                item = {"message_id": obj.id, "conversation_id": obj.meta_info.get("conversation_id")}
            elif isinstance(obj, ChunkRead):
                item = {"chunk_id": obj.id}
            elif isinstance(obj, CollectionRead):
                # Optionally handle nested collections or skip
                continue
            elif hasattr(obj, 'target_type') and hasattr(obj, 'id'):
                # Handle AgentOutput objects from gencom search results
                # We can't directly add agent outputs to collections,
                # but we can add their target objects if available
                if hasattr(obj, 'target_id') and obj.target_id:
                    if obj.target_type == 'message':
                        item = {"message_id": obj.target_id}
                    elif obj.target_type == 'conversation':
                        item = {"conversation_id": obj.target_id}
                    elif obj.target_type == 'chunk':
                        item = {"chunk_id": obj.target_id}
                    else:
                        # Skip if unknown target type
                        continue
                else:
                    # Skip if no target_id available
                    continue
            else:
                # Skip unknown object types
                continue
                
            items.append(item)

        # Convert dicts to CollectionItemSchema instances
        from carchive.collections.schemas import CollectionItemSchema
        item_schemas = [CollectionItemSchema(**i) for i in items]

        coll_data = CollectionCreateSchema(name=name, meta_info=meta_info, items=item_schemas)
        return CollectionManager.create_collection(coll_data)

    @staticmethod
    def get_items_as_dbobjects(collection_id: uuid.UUID) -> List[DBObject]:
        """
        Fetches items from a collection, returns them as DBObjects
        (MessageRead, ChunkRead, ConversationRead, etc.).
        """
        from carchive.utils.conversions import convert_to_pydantic
        with get_session() as session:
            items = session.query(CollectionItem).filter_by(collection_id=collection_id).all()
            results = []
            for it in items:
                # If item.message_id, fetch message, convert to pydantic
                if it.message_id:
                    msg = session.query(Message).filter_by(id=it.message_id).first()
                    if msg:
                        results.append(convert_to_pydantic(msg))
                elif it.chunk_id:
                    ch = session.query(Chunk).filter_by(id=it.chunk_id).first()
                    if ch:
                        results.append(convert_to_pydantic(ch))
                elif it.conversation_id:
                    cv = session.query(Conversation).filter_by(id=it.conversation_id).first()
                    if cv:
                        results.append(convert_to_pydantic(cv))
                # skip others
            return results
