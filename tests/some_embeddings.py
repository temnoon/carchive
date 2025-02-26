# File: tests/some_embedding.py

import logging
from sqlalchemy import func
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, Embedding
from carchive.embeddings.embed import embed_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def embed_messages_in_active_conversations():
    """
    Embeds messages from conversations with >3 non-blank messages,
    using the Ollama agent (nomic-text-embed model).
    """
    with get_session() as session:
        # Query for conversations with >3 non-blank messages
        conversation_ids = (
            session.query(Conversation.id)
            .join(Message)
            .filter(Message.content.isnot(None), Message.content != "")
            .group_by(Conversation.id)
            .having(func.count(Message.id) > 3)
            .all()
        )

        # Extract just the UUIDs from the query result
        conversation_ids = [row[0] for row in conversation_ids]
        logger.info(f"Found {len(conversation_ids)} conversations with >3 non-blank messages.")

        for conv_id in conversation_ids:
            # Get all non-blank messages for this conversation
            messages = (
                session.query(Message)
                .filter(
                    Message.conversation_id == conv_id,
                    Message.content.isnot(None),
                    Message.content != "",
                )
                .all()
            )

            logger.info(f"Conversation {conv_id} has {len(messages)} messages to embed.")

            for msg in messages:
                # Check if we've already embedded this message
                existing_embedding = (
                    session.query(Embedding)
                    .filter_by(parent_message_id=msg.id)
                    .first()
                )
                if existing_embedding:
                    logger.debug(f"Message {msg.id} already has an embedding; skipping.")
                    continue

                try:
                    # Convert msg.content to string for embedding
                    message_content = str(msg.content)
                    # Force the Ollama provider here
                    emb_obj = embed_text(
                        text=message_content,
                        provider="ollama",
                        model_version="nomic-embed-text"
                    )
                    if emb_obj:
                        emb_obj.parent_message_id = msg.id
                        session.add(emb_obj)
                        session.commit()
                        logger.info(f"Embedded message {msg.id}.")
                except Exception as exc:
                    logger.error(f"Error embedding message {msg.id}: {exc}")
                    session.rollback()

if __name__ == "__main__":
    embed_messages_in_active_conversations()
