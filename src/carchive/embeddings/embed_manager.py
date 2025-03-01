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
        
        # Check for empty targets
        if not request_data.targets:
            logger.warning("No targets provided for embedding")
            return results
            
        with get_session() as session:
            # Process targets and generate embeddings
            embedding_objects = []
            
            for t in request_data.targets:
                try:
                    if t.text is not None:
                        vector = agent.generate_embedding(t.text)
                        try:
                            # Try to see if parent_type column exists and is required
                            emb_obj = Embedding(
                                id=uuid.uuid4(),
                                model_name=request_data.provider,
                                model_version=request_data.model_version,
                                dimensions=len(vector),
                                vector=vector,
                                parent_type="raw_text",  # Default for raw text with no parent
                                meta_info={"source": "raw_text"}
                            )
                        except Exception:
                            # Fallback if parent_type doesn't exist or some other issue
                            emb_obj = Embedding(
                                id=uuid.uuid4(),
                                model_name=request_data.provider,
                                model_version=request_data.model_version,
                                dimensions=len(vector),
                                vector=vector,
                                meta_info={"source": "raw_text"}
                            )
                        if request_data.store_in_db:
                            embedding_objects.append(emb_obj)
                        results.append(EmbeddingResultSchema(db_id=str(emb_obj.id), vector=vector))
                    elif t.message_id or t.chunk_id:
                        content = ""
                        if t.message_id:
                            msg = session.query(Message).filter_by(id=t.message_id).first()
                            content = msg.content if msg else ""
                        elif t.chunk_id:
                            ch = session.query(Chunk).filter_by(id=t.chunk_id).first()
                            content = ch.content if ch else ""

                        if not content:
                            logger.warning(f"Skipping empty content for {'message' if t.message_id else 'chunk'} {t.message_id or t.chunk_id}")
                            continue

                        vector = agent.generate_embedding(str(content))
                        
                        # Create the embedding object with the appropriate parent ID
                        # Be careful with the column names to ensure they exist in the DB schema
                        try:
                            # Use the most appropriate method based on available columns
                            try:
                                # Try checking if the parent_type and parent_id columns exist
                                # by executing a simple query to see if records with these fields exist
                                with get_session() as check_session:
                                    has_parent_type = check_session.query(
                                        check_session.query(Embedding).filter(
                                            Embedding.parent_type.isnot(None)
                                        ).exists()
                                    ).scalar()
                                                                    
                                if has_parent_type:
                                    # Use parent_type and parent_id approach, defaulting for text embeddings
                                    if t.message_id:
                                        parent_type = "message"
                                        parent_id = t.message_id
                                    elif t.chunk_id:
                                        parent_type = "chunk"
                                        parent_id = t.chunk_id
                                    else:
                                        # For raw text, we don't have parent references
                                        parent_type = "raw_text"
                                        parent_id = None
                                    
                                    emb_obj = Embedding(
                                        id=uuid.uuid4(),
                                        model_name=request_data.provider,
                                        model_version=request_data.model_version,
                                        dimensions=len(vector),
                                        vector=vector,
                                        parent_type=parent_type,
                                        parent_id=parent_id,
                                        parent_message_id=t.message_id,
                                        parent_chunk_id=t.chunk_id,
                                        meta_info={"source": "db_ref" if t.message_id or t.chunk_id else "raw_text"}
                                    )
                                else:
                                    # Use specific parent columns
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
                            except Exception as inner_e:
                                logger.warning(f"Could not determine parent column approach: {inner_e}")
                                # Use specific parent columns as default
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
                                
                        except Exception as e:
                            logger.error(f"Error creating embedding object: {e}")
                            # Fallback to a version with just meta_info
                            emb_obj = Embedding(
                                id=uuid.uuid4(),
                                model_name=request_data.provider,
                                model_version=request_data.model_version,
                                dimensions=len(vector),
                                vector=vector,
                                meta_info={"source": "db_ref", 
                                          "message_id": str(t.message_id) if t.message_id else None,
                                          "chunk_id": str(t.chunk_id) if t.chunk_id else None}
                            )
                            
                        if request_data.store_in_db:
                            embedding_objects.append(emb_obj)
                        results.append(EmbeddingResultSchema(db_id=str(emb_obj.id), vector=vector))
                except Exception as e:
                    logger.error(f"Error processing embedding target: {e}")
                    # Continue with the rest of the targets
                    continue

            # Store all embeddings in the database in a single transaction
            if request_data.store_in_db and embedding_objects:
                try:
                    # Add all objects to the session
                    for obj in embedding_objects:
                        session.add(obj)
                    # Commit the transaction
                    session.commit()
                except Exception as e:
                    logger.error(f"Error storing embeddings in database: {e}")
                    session.rollback()
                    # Since we couldn't store them, mark as not stored in results
                    for result in results:
                        result.stored = False

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
        store_in_db: bool = True,
        resume: bool = True
    ) -> int:
        """
        Embed all messages with more than `min_word_count` words.

        :param options: EmbedAllOptions instance with filtering criteria.
        :param provider: Embedding provider to use. If None, uses default.
        :param model_version: Specific model version to use. If None, uses default.
        :param store_in_db: Whether to store the embeddings in the database.
        :param resume: Whether to skip messages that already have embeddings with the same model.
        :return: Number of messages embedded.
        """
        provider = provider or DEFAULT_EMBEDDING_PROVIDER
        model_version = model_version or DEFAULT_EMBEDDING_MODEL

        # Initialize the embedding agent
        agent = AgentManager().get_embedding_agent(provider)

        with get_session() as session:
            # Use specific column selection to avoid querying non-existent columns
            query = session.query(
                Message.id,
                Message.conversation_id, 
                Message.source_id,
                Message.parent_id,
                Message.role,
                Message.author_name,
                Message.content,
                Message.content_type,
                Message.created_at,
                Message.updated_at,
                Message.status,
                Message.position,
                Message.weight,
                Message.end_turn,
                Message.meta_info
            )

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
                query = query.filter(Message.role.in_(options.include_roles))
                
            # If resuming, exclude messages that already have embeddings with this model
            if resume:
                try:
                    # Check if parent_message_id column exists in the database
                    session.query(Embedding.parent_message_id).limit(1).all()
                    
                    # If we reach this point, the column exists
                    has_parent_columns = True
                    
                    # Get IDs of messages that already have embeddings with this model
                    existing_ids_query = session.query(Embedding.parent_message_id).filter(
                        Embedding.model_name == provider,
                        Embedding.model_version == model_version,
                        Embedding.parent_message_id.isnot(None)
                    )
                    
                    existing_message_ids = [r[0] for r in existing_ids_query.all()]
                    logger.info(f"Found {len(existing_message_ids)} messages that already have embeddings with model {provider}/{model_version}")
                    
                    if existing_message_ids:
                        query = query.filter(~Message.id.in_(existing_message_ids))
                        
                except Exception as e:
                    logger.warning(f"Could not filter already embedded messages: {e}")
                    logger.warning("Will attempt to create embeddings for all qualifying messages.")
            
            # Execute query with explicit columns
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

            # Process in batches to avoid overwhelming the database or memory
            batch_size = 100
            total_processed = 0
            
            for i in range(0, len(targets), batch_size):
                batch_targets = targets[i:i+batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} of {(len(targets) + batch_size - 1)//batch_size} ({len(batch_targets)} messages)")
                
                embedding_request = EmbeddingRequestSchema(
                    provider=provider,
                    model_version=model_version,
                    store_in_db=store_in_db,
                    targets=batch_targets
                )

                try:
                    # Generate embeddings for this batch
                    results = self.embed_texts(embedding_request)
                    total_processed += len(results)
                    logger.info(f"Generated embeddings for {len(results)} messages in this batch. Total: {total_processed}")
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    logger.info(f"Successfully processed {total_processed} messages before error")
                    return total_processed

            logger.info(f"Generated embeddings for a total of {total_processed} messages.")
            return total_processed

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

                # Explicitly select only the columns that exist in the messages table
                query = session.query(
                    Message.id,
                    Message.conversation_id,
                    Message.source_id,
                    Message.parent_id,
                    Message.role,
                    Message.author_name,
                    Message.content,
                    Message.content_type,
                    Message.created_at,
                    Message.updated_at,
                    Message.status,
                    Message.position,
                    Message.weight,
                    Message.end_turn,
                    Message.meta_info
                ).join(
                    Embedding, Embedding.parent_message_id == Message.id
                ).outerjoin(
                    AgentOutput,
                    (AgentOutput.target_type == 'message') &
                    (AgentOutput.target_id == Message.id) &
                    (AgentOutput.output_type == 'summary')
                ).filter(
                    AgentOutput.id.is_(None)
                ).filter(
                    word_count_expr >= min_word_count
                )

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
