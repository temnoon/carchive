# carchive2/src/carchive2/search/search_manager.py

import json
from typing import List
from carchive.search.search import search_messages, search_conversations
from carchive.embeddings.embed_manager import EmbeddingManager
from carchive.collections.collection_manager import CollectionManager
from carchive.schemas.db_objects import MessageRead, ConversationRead
from carchive.embeddings.schemas import EmbeddingRequestSchema, EmbeddingTargetSchema
from carchive.collections.schemas import CollectionCreateSchema, CollectionItemSchema

class SearchManager:
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        self.collection_manager = CollectionManager()

    def search_and_create_collection(
        self,
        criteria_file: str,
        collection_name: str,
        search_type: str = "message",
        embed: bool = False
    ):
        # Load criteria from file
        with open(criteria_file, "r", encoding="utf-8") as f:
            criteria_data = json.load(f)

        text_query = criteria_data.get("text_query", "")
        top_k = criteria_data.get("top_k", 10)

        # Execute search based on type
        if search_type == "message":
            results: List[MessageRead] = search_messages(text_query, limit=top_k)
        elif search_type == "conversation":
            results: List[ConversationRead] = search_conversations(text_query, limit=top_k)
        else:
            raise ValueError("Unsupported search type.")

        if not results:
            raise ValueError(f"No results found for query: '{text_query}'")

        # Optionally run embeddings on results
        if embed:
            targets = []
            for obj in results:
                # For simplicity, we'll only embed messages; expand as needed
                if isinstance(obj, MessageRead):
                    targets.append(EmbeddingTargetSchema(text=obj.content))
            embedding_request = EmbeddingRequestSchema(
                provider="ollama",
                model_version="nomic-embed-text",
                store_in_db=True,
                targets=targets
            )
            self.embedding_manager.embed_texts(embedding_request)

        # Prepare collection items from results
        items = []
        for obj in results:
            if search_type == "message" and isinstance(obj, MessageRead):
                items.append(CollectionItemSchema(
                    message_id=obj.id,
                    conversation_id=obj.conversation_id
                ))
            elif search_type == "conversation" and isinstance(obj, ConversationRead):
                items.append(CollectionItemSchema(
                    conversation_id=obj.id
                ))
            # Extend for other types as needed

        coll_data = CollectionCreateSchema(name=collection_name, items=items)
        collection = self.collection_manager.create_collection(coll_data)
        return collection
