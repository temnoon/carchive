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
    role = Column(String, nullable=False)  # user, assistant, system, tool, etc.
    author_name = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    content_type = Column(String, nullable=True)  # text, code, multimodal_text, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, nullable=True)  # finished_successfully, etc.
    position = Column(Integer, nullable=True)  # ordered position in conversation
    weight = Column(Integer, nullable=True)  # for weighted conversations (float in DB)
    end_turn = Column(Boolean, default=True)  # message ends a turn
    meta_info = Column(JSONB, nullable=True)
    
    # Remove media_id column as it doesn't exist in the actual database schema
    # and media associations are handled through the message_media table

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    # Self-reference for parent-child relationship
    children = relationship("Message", 
                          back_populates="parent", 
                          remote_side=[id])
    parent = relationship("Message", 
                         back_populates="children", 
                         foreign_keys=[parent_id])
    media_associations = relationship(
        "MessageMedia", 
        back_populates="message",
        overlaps="media_items"
    )
    media_items = relationship(
        "Media", 
        secondary="message_media",
        overlaps="media_associations",
        viewonly=True  # Make this relationship read-only to prevent sync issues
    )
    chunks = relationship("Chunk", back_populates="message")
    embeddings = relationship("Embedding", foreign_keys="[Embedding.parent_message_id]", back_populates="parent_message")

class Chunk(Base):
    """Represents a chunk of a message for processing (e.g., embeddings)."""
    __tablename__ = "chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"))
    content = Column(Text, nullable=True)
    chunk_type = Column(String, nullable=True)  # Type of chunk (e.g., 'paragraph', 'sentence', 'custom')
    position = Column(Integer, default=0)  # Order of chunks within a message
    start_char = Column(Integer, nullable=True)  # Starting character position in original text
    end_char = Column(Integer, nullable=True)  # Ending character position in original text
    meta_info = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="chunks")
    embeddings = relationship("Embedding", foreign_keys="[Embedding.parent_chunk_id]", back_populates="parent_chunk")

class ResultsBuffer(Base):
    """Stores collections of search results and other entities."""
    __tablename__ = "results_buffers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    buffer_type = Column(String, nullable=False)  # ephemeral, session, persistent
    session_id = Column(String, nullable=True)  # For session-scoped buffers
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    meta_info = Column(JSONB, nullable=True)
    
    # Relationships
    items = relationship("BufferItem", back_populates="buffer", cascade="all, delete-orphan")
    
class BufferItem(Base):
    """Links buffer to various entities."""
    __tablename__ = "buffer_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buffer_id = Column(UUID(as_uuid=True), ForeignKey("results_buffers.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True)
    gencom_id = Column(UUID(as_uuid=True), ForeignKey("agent_outputs.id", ondelete="SET NULL"), nullable=True)
    position = Column(Integer, nullable=False)
    meta_info = Column(JSONB, nullable=True)
    
    # Relationships
    buffer = relationship("ResultsBuffer", back_populates="items")
    message = relationship("Message", foreign_keys=[message_id])
    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    chunk = relationship("Chunk", foreign_keys=[chunk_id])
    agent_output = relationship("AgentOutput", foreign_keys=[gencom_id], back_populates="buffer_items")

class Media(Base):
    """Represents media files associated with messages."""
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_path = Column(String, nullable=False)  # Path to the stored media file
    media_type = Column(String, nullable=False)  # e.g., 'image', 'pdf', 'audio'
    provider_id = Column(UUID(as_uuid=True), ForeignKey("providers.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional fields in the database
    original_file_name = Column(String, nullable=True)  # Original file name (without path)
    original_file_id = Column(String, nullable=True)  # Original file ID from source system
    mime_type = Column(String, nullable=False, default="application/octet-stream")  # MIME type
    file_size = Column(Integer, nullable=True)  # Size in bytes
    checksum = Column(String, nullable=True)  # File checksum for verification
    is_generated = Column(Boolean, server_default='false', nullable=False)  # AI generated flag
    source_url = Column(String, nullable=True)  # URL source if applicable
    meta_info = Column(JSONB, nullable=True)  # Metadata stored as JSONB
    
    # Relationships
    message_associations = relationship("MessageMedia", back_populates="media", overlaps="media_items")
    provider = relationship("Provider")
    
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
    
    # Relationship to buffer items
    buffer_items = relationship("BufferItem", foreign_keys="[BufferItem.gencom_id]")
    
class MessageMedia(Base):
    """Links messages to media items with association type."""
    __tablename__ = "message_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    association_type = Column(String, nullable=True)  # 'uploaded', 'generated', etc.
    
    # Relationships
    message = relationship("Message", back_populates="media_associations", overlaps="media_items")
    media = relationship("Media", back_populates="message_associations", overlaps="media_items")

class Embedding(Base):
    """Stores vector embeddings for messages or chunks."""
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String, nullable=False)  # e.g., 'bert', 'openai'
    model_version = Column(String, nullable=True)
    dimensions = Column(Integer, nullable=False)  # Embedding dimension
    vector = Column(Vector(768))  # Using 768 dimensions for nomic-embed-text model
    
    # Support for both parent_id/parent_type pattern and direct linking
    parent_type = Column(String, nullable=True)  # 'conversation', 'message', 'chunk', 'media'
    parent_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Specific parent relationships
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    parent_chunk_id = Column(UUID(as_uuid=True), ForeignKey("chunks.id"), nullable=True)
    
    # Relationships to parent entities
    parent_message = relationship("Message", foreign_keys=[parent_message_id], back_populates="embeddings")
    parent_chunk = relationship("Chunk", foreign_keys=[parent_chunk_id], back_populates="embeddings")
    
    embedding_type = Column(String, nullable=True)  # 'query', 'document', 'hybrid'
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
    conversation = relationship("Conversation", foreign_keys=[conversation_id])
    message = relationship("Message", foreign_keys=[message_id])
    chunk = relationship("Chunk", foreign_keys=[chunk_id])

class SavedSearch(Base):
    """Represents a saved search query and criteria."""
    __tablename__ = "saved_searches"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    query = Column(String, nullable=False)
    search_type = Column(String, nullable=False, default="all")
    criteria = Column(JSONB, nullable=True)  # Store search criteria as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Optionally link to a user if user management is implemented
    user_id = Column(UUID(as_uuid=True), nullable=True)
