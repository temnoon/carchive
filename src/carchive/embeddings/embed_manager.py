# carchive2/src/carchive2/embeddings/embed_manager.py

from typing import List, Optional
import uuid
import logging
from sqlalchemy import func
from carchive.database.session import get_session
from carchive.database.models import Message, Embedding, AgentOutput
from carchive.agents.manager import AgentManager
from carchive.embeddings.schemas import (
    EmbeddingRequestSchema,
    EmbeddingTargetSchema,
    EmbeddingResultSchema,
    EmbedAllOptions
)
from carchive.collections.schemas import CollectionCreateSchema, CollectionItemSchema
from carchive.schemas.db_objects import MessageRead, ChunkRead, DBObject
from carchive.core.config import DEFAULT_EMBEDDING_PROVIDER, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger(__name__)

class EmbeddingManager:
    def embed_texts(self, request_data: EmbeddingRequestSchema) -> List[EmbeddingResultSchema]:
        """
        Takes a list of texts or DB references, generates embeddings, and returns them.
        Also persists to DB if 'store_in_db' is True.
        """
        agent = AgentManager().get_embedding_agent(request_data.provider or DEFAULT_EMBEDDING_PROVIDER)
        results = []
        with get_session() as session:
            for t in request_data.targets:
                if t.text is not None:
                    vector = agent.generate_embedding(t.text)
                    emb_obj = Embedding(
                        id=uuid.uuid4(),
                        model_name=request_data.provider,
                        model_version=request_data.model_version,
                        dimensions=len(vector),
                        vector=vector,
                        meta_info={"source": "raw_text"}
                    )
                    if request_data.store_in_db:
                        session.add(emb_obj)
                    results.append(EmbeddingResultSchema(db_id=str(emb_obj.id), vector=vector))
                elif t.message_id or t.chunk_id:
                    content = ""
                    if t.message_id:
                        msg = session.query(Message).filter_by(id=t.message_id).first()
                        content = msg.content if msg else ""
                    elif t.chunk_id:
                        ch = session.query(Chunk).filter_by(id=t.chunk_id).first()
                        content = ch.content if ch else ""

                    vector = agent.generate_embedding(str(content))
                    emb_obj = Embedding(
                        id=uuid.uuid4(),
                        model_name=request_data.provider,
                        model_version=request_data.model_version,
                        dimensions=len(vector),
                        vector=vector,
                        parent_message_id=t.message_id,
                        parent_chunk_id=t.chunk_id,
                        meta_info={"source": "db_ref"}
                    )
                    if request_data.store_in_db:
                        session.add(emb_obj)
                    results.append(EmbeddingResultSchema(db_id=str(emb_obj.id), vector=vector))

            if request_data.store_in_db:
                session.commit()

        return results

    def embed_dbobjects(
        self,
        objects: List[DBObject],
        provider: str = "ollama",
        model_version: str = "nomic-embed-text",
        store_in_db: bool = True
    ):
        """
        Takes a list of DBObject (which could be messages or chunks),
        builds an EmbeddingRequestSchema, and calls embed_texts.
        """
        targets = []
        for obj in objects:
            if isinstance(obj, MessageRead):
                targets.append(EmbeddingTargetSchema(
                    message_id=obj.id
                ))
            elif isinstance(obj, ChunkRead):
                targets.append(EmbeddingTargetSchema(
                    chunk_id=obj.id
                ))
            else:
                continue

        request_data = EmbeddingRequestSchema(
            provider=provider,
            model_version=model_version,
            store_in_db=store_in_db,
            targets=targets
        )

        return self.embed_texts(request_data)

    def embed_all_messages (
        self,
        options: EmbedAllOptions,
        provider: Optional[str] = None,
        model_version: Optional[str] = None,
        store_in_db: bool = True
    ) -> int:
        """
        Embed all messages with more than `min_word_count` words.

        :param options: EmbedAllOptions instance with filtering criteria.
        :param provider: Embedding provider to use. If None, uses default.
        :param model_version: Specific model version to use. If None, uses default.
        :param store_in_db: Whether to store the embeddings in the database.
        :return: Number of messages embedded.
        """
        provider = provider or DEFAULT_EMBEDDING_PROVIDER
        model_version = model_version or DEFAULT_EMBEDDING_MODEL

        # Initialize the embedding agent
        agent = AgentManager().get_embedding_agent(provider)

        with get_session() as session:
            # Query messages based on criteria
            query = session.query(Message)

            if options.exclude_empty:
                query = query.filter(Message.content.isnot(None), Message.content != "")

            # Calculate word count using SQL
            from sqlalchemy import func, cast, Integer
            from sqlalchemy.sql import expression

            word_count_expr = func.array_length(
                func.regexp_split_to_array(Message.content, r'\s+'), 1
            )
            query = query.filter(word_count_expr > options.min_word_count)

            if options.include_roles:
                query = query.filter(Message.meta_info['author_role'].as_string().in_(options.include_roles))
            qualifying_messages = query.all()
            logger.info(f"Found {len(qualifying_messages)} messages to embed based on criteria.")

            if not qualifying_messages:
                logger.info("No messages found matching the criteria.")
                return 0

            # Prepare embedding targets
            targets = []
            for msg in qualifying_messages:
                targets.append(EmbeddingTargetSchema(
                    text=msg.content,
                    message_id=msg.id
                ))

            embedding_request = EmbeddingRequestSchema(
                provider=provider,
                model_version=model_version,
                store_in_db=store_in_db,
                targets=targets
            )

            # Generate embeddings
            results = self.embed_texts(embedding_request)
            logger.info(f"Generated embeddings for {len(results)} messages.")

            return len(results)

    def summarize_messages(
            self,
            model_name: Optional[str] = None,
            provider: str = "llama3.2",
            min_word_count: int = 5,
            limit: Optional[int] = None
    ) -> int:
            """
            Generate summaries for all messages that have embeddings and meet the word count criteria.

            :param model_name: The model to use for summarization. If None, use default 'llama3.2'.
            :param provider: The provider to use for summarization.
            :param min_word_count: Minimum number of words in a message to qualify for summarization.
            :param limit: Optional limit on the number of messages to summarize.
            :return: Number of messages summarized.
            """
            logger.info(f"Starting summarization with model='{model_name or 'llama3.2'}', provider='{provider}', min_word_count={min_word_count}, limit={limit}")

            # Initialize the summarization agent
            agent = AgentManager().get_chat_agent(provider)

            with get_session() as session:
                # Calculate word count using SQL
                word_count_expr = func.array_length(
                    func.regexp_split_to_array(Message.content, r'\s+'), 1
                )

                # Fetch messages that have embeddings, meet word count, and have no summary yet
                query = session.query(Message).join(Embedding, Embedding.parent_message_id == Message.id)\
                    .outerjoin(AgentOutput,
                               (AgentOutput.target_type == 'message') &
                               (AgentOutput.target_id == Message.id) &
                               (AgentOutput.output_type == 'summary'))\
                    .filter(AgentOutput.id.is_(None))\
                    .filter(word_count_expr >= min_word_count)

                if limit:
                    query = query.limit(limit)

                messages = query.all()

                total_messages = len(messages)
                logger.info(f"Found {total_messages} messages to summarize.")

                if not messages:
                    logger.info("No messages require summarization.")
                    return 0

                # Batch processing (optional)
                batch_size = 10
                for i in range(0, total_messages, batch_size):
                    batch = messages[i:i+batch_size]
                    texts = [msg.content for msg in batch]
                    summaries = agent.generate_summaries(texts)

                    for msg, summary in zip(batch, summaries):
                        if summary:
                            # Create a new AgentOutput entry
                            agent_output = AgentOutput(
                                target_type='message',
                                target_id=msg.id,
                                output_type='summary',
                                content=summary,
                                agent_name=agent.agent_name  # Ensure Agent class has this attribute
                            )
                            session.add(agent_output)
                            logger.debug(f"Summarized message ID {msg.id}")
                        else:
                            logger.warning(f"Failed to generate summary for message ID {msg.id}")

                session.commit()
                logger.info(f"Successfully summarized {total_messages} messages.")

            return total_messages
