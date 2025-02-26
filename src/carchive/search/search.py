# carchive2/search/search.py

from typing import List
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, Embedding, Collection, CollectionItem
from carchive.schemas.db_objects import ConversationRead, MessageRead

from carchive.schemas.db_objects import MessageWithConversationRead

def search_conversations(query: str, limit: int = 10) -> List[ConversationRead]:
    """
    Simple substring search in conversation titles.
    Returns a list of ConversationRead objects.
    """
    with get_session() as session:
        results = session.query(Conversation)\
                         .filter(Conversation.title.ilike(f"%{query}%"))\
                         .limit(limit)\
                         .all()
    return [ConversationRead.from_orm(c) for c in results]

def search_messages(query: str, limit: int = 10) -> List[MessageRead]:
    """
    Search for messages that contain the given query text.
    Returns a list of MessageRead objects.
    """
    with get_session() as session:
        results = session.query(Message)\
                         .filter(Message.content.ilike(f"%{query}%"))\
                         .limit(limit)\
                         .all()
    return [MessageRead.from_orm(m) for m in results]

def vector_search(anchor_vector: List[float], top_k: int = 5) -> List[Embedding]:
    """
    Example pgvector similarity search.
    """
    with get_session() as session:
        results = session.query(Embedding)\
                         .order_by(Embedding.vector.l2_distance(anchor_vector))\
                         .limit(top_k)\
                         .all()
    return results

def create_collection_from_vector(name: str, anchor_vector: List[float], top_k: int = 5):
    """
    Create a collection from the top_k vector results.
    """
    with get_session() as session:
        coll = Collection(name=name)
        session.add(coll)
        session.flush()

        top_embs = session.query(Embedding)\
                          .order_by(Embedding.vector.l2_distance(anchor_vector))\
                          .limit(top_k)\
                          .all()

        for emb in top_embs:
            item = CollectionItem(
                collection_id=coll.id,
                message_id=emb.parent_message_id,
                chunk_id=emb.parent_chunk_id,
                meta_info={"embedding_id": str(emb.id)}
            )
            session.add(item)

        session.commit()
        session.refresh(coll)
    return coll


def search_messages_with_conversation(query: str, limit: int = 10) -> List[MessageWithConversationRead]:
    """
    Searches messages along with conversation info.
    Returns a list of MessageWithConversationRead models.
    """
    with get_session() as session:
        query_result = (
            session.query(
                Message.id.label('message_id'),
                Message.content,
                Conversation.id.label('conversation_id'),
                Conversation.title.label('conversation_title'),
                Conversation.created_at.label('conversation_created_at')
            )
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Message.content.ilike(f"%{query}%"))
            .limit(limit)
            .all()
        )

    results = []
    for row in query_result:
        mwc = MessageWithConversationRead(
            message_id=row.message_id,
            content=row.content,
            conversation_id=row.conversation_id,
            conversation_title=row.conversation_title,
            conversation_created_at=row.conversation_created_at
        )
        results.append(mwc)
    return results
