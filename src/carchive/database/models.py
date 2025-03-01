# src/carchive/database/models.py

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

# Create the base class for SQLAlchemy models
Base = declarative_base()

class Provider(Base):
    """Represents a model provider (e.g., 'chatgpt', 'claude')."""
    __tablename__ = "providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to conversations
    conversations = relationship("Conversation", back_populates="provider")

class Conversation(Base):
    """Represents a conversation thread."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=True)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True)
    source_id = Column(String, nullable=True)  # original id from source system
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    source_created_at = Column(DateTime(timezone=True), nullable=True)
    source_updated_at = Column(DateTime(timezone=True), nullable=True)
    first_message_time = Column(DateTime(timezone=True), nullable=True)
    last_message_time = Column(DateTime(timezone=True), nullable=True)
    model_info = Column(JSONB, nullable=True)  # store model info (name, version)
    is_archived = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    current_node_id = Column(String, nullable=True)  # for chat thread navigation
    meta_info = Column(JSONB, nullable=True)  # Metadata stored as JSONB for flexibility

    # Relationships
    provider = relationship("Provider", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    """Represents a single message in a conversation."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    source_id = Column(String, nullable=True)  # original ID from the source system
    parent_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    role = Column(String, nullable=True)  # user, assistant, system, tool, etc.
    author_name = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    content_type = Column(String, nullable=True)  # text, code, multimodal_text, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=True)  # finished_successfully, etc.
    position = Column(Integer, nullable=True)  # ordered position in conversation
    weight = Column(Integer, nullable=True)  # for weighted conversations
    end_turn = Column(Boolean, default=True)  # message ends a turn
    meta_info = Column(JSONB, nullable=True)
    # Legacy field, kept for backward compatibility
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    # Self-reference for parent-child relationship
    children = relationship("Message", 
                           backref="parent", 
                           remote_side=[id])
    media_associations = relationship(
        "MessageMedia", 
        back_populates="message",
        overlaps="media_items"
    )
    media_items = relationship(
        "Media", 
        secondary="message_media",
        overlaps="media_associations,messages"
    )
    chunks = relationship("Chunk", back_populates="message")

class Chunk(Base):
    """Represents a chunk of a message for processing (e.g., embeddings)."""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    content = Column(Text, nullable=True)
    position = Column(Integer, default=0)  # Order of chunks within a message
    meta_info = Column(JSONB, nullable=True)

    # Relationship
    message = relationship("Message", back_populates="chunks")

class Media(Base):
    """Represents media files associated with messages."""
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False)  # Path to the stored media file
    media_type = Column(String, nullable=False)  # e.g., 'image', 'pdf', 'audio'
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    original_file_id = Column(String, nullable=True, index=True)  # The ID from file-XXXX
    original_file_name = Column(String, nullable=True)  # Original file name
    file_name = Column(String, nullable=True)  # Current file name
    mime_type = Column(String, nullable=True)  # MIME type of the file
    file_size = Column(Integer, nullable=True)  # Size in bytes
    checksum = Column(String, nullable=True)  # For duplicate detection
    source_url = Column(String, nullable=True)  # URL for remote files or local reference
    is_generated = Column(Boolean, default=False)  # Whether this was generated by AI
    meta_info = Column(JSONB, nullable=True)  # Additional metadata

    # Relationships
    provider = relationship("Provider")
    message_associations = relationship(
        "MessageMedia", 
        back_populates="media",
        overlaps="messages,media_items"
    )
    messages = relationship(
        "Message", 
        secondary="message_media",
        overlaps="message_associations,media_associations,media_items"
    )
    
class MessageMedia(Base):
    """Links messages to media items with association type."""
    __tablename__ = "message_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    association_type = Column(String, nullable=True)  # 'uploaded', 'generated', etc.
    
    # Relationships
    message = relationship(
        "Message", 
        back_populates="media_associations",
        overlaps="media_items,messages"
    )
    media = relationship(
        "Media", 
        back_populates="message_associations",
        overlaps="messages,media_items"
    )

class Embedding(Base):
    """Stores vector embeddings for messages or chunks."""
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String, nullable=False)  # e.g., 'bert', 'openai'
    model_version = Column(String, nullable=True)
    dimensions = Column(Integer, nullable=False)  # Embedding dimension
    vector = Column(Vector(768))  # Adjust dimension based on model (e.g., 768 for BERT)
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    meta_info = Column(JSONB, nullable=True)

class Collection(Base):
    """Represents a collection of conversations, messages, or chunks."""
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    meta_info = Column(JSONB, nullable=True)

    # Relationship
    items = relationship("CollectionItem", back_populates="collection")

class CollectionItem(Base):
    """Links items (conversations, messages, chunks) to collections."""
    __tablename__ = "collection_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id"))
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    meta_info = Column(JSONB, nullable=True)

    # Relationship
    collection = relationship("Collection", back_populates="items")

class AgentOutput(Base):
    """Stores outputs from agent (e.g., LLM) processing."""
    __tablename__ = "agent_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type = Column(String, nullable=False)  # e.g., 'message', 'conversation', 'chunk'
    target_id = Column(UUID(as_uuid=True), nullable=False)  # ID of the target
    output_type = Column(String, nullable=False)  # e.g., 'summary', 'review'
    content = Column(Text, nullable=False)  # The generated output
    agent_name = Column(String, nullable=False)  # e.g., 'llama3.2'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
