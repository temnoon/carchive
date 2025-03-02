"""
Chunker module for breaking text content into chunks.

This module provides strategies and utilities for breaking long text content
into smaller, manageable chunks for processing, embedding, and search.
"""

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum
import logging
from datetime import datetime

from carchive.database.session import get_session
from carchive.database.models import Message, Chunk

logger = logging.getLogger(__name__)


class ChunkType(str, Enum):
    """Enumeration of supported chunk types."""
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    TOKEN = "token"
    FIXED_LENGTH = "fixed_length"
    CUSTOM = "custom"


class ChunkResult:
    """Represents the result of a chunking operation."""
    
    def __init__(self, chunks: List[Chunk], count: int, metadata: Dict[str, Any] = None):
        """
        Initialize a ChunkResult.
        
        Args:
            chunks: List of created Chunk instances
            count: Number of chunks created
            metadata: Optional metadata about the chunking operation
        """
        self.chunks = chunks
        self.count = count
        self.metadata = metadata or {}


class ChunkerOptions:
    """Configuration options for chunking strategies."""
    
    def __init__(
        self,
        chunk_type: ChunkType = ChunkType.PARAGRAPH,
        chunk_size: int = 512,
        chunk_overlap: int = 0,
        min_chunk_size: int = 50,
        stop_strings: List[str] = None,
        separator: str = None,
        keep_separator: bool = False,
    ):
        """
        Initialize chunking options.
        
        Args:
            chunk_type: Type of chunking strategy to use
            chunk_size: Maximum size of chunks (for fixed_length)
            chunk_overlap: Overlap between chunks (for fixed_length)
            min_chunk_size: Minimum size of chunks
            stop_strings: List of strings that mark chunk boundaries
            separator: String used to separate chunks
            keep_separator: Whether to keep separators in chunks
        """
        self.chunk_type = chunk_type
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.stop_strings = stop_strings or []
        self.separator = separator
        self.keep_separator = keep_separator


class Chunker:
    """
    Utility class for creating chunks from text content.
    
    This class provides methods for breaking down message content into
    smaller chunks using various strategies (paragraph, sentence, token, etc.).
    """
    
    @staticmethod
    def chunk_message(
        message_id: uuid.UUID, 
        options: ChunkerOptions = None
    ) -> ChunkResult:
        """
        Create chunks from a message.
        
        Args:
            message_id: UUID of the message to chunk
            options: Chunking options
            
        Returns:
            A ChunkResult containing the created chunks and metadata
        """
        options = options or ChunkerOptions()
        
        with get_session() as session:
            # Get message
            message = session.query(Message).filter(Message.id == message_id).first()
            if not message or not message.content:
                logger.warning(f"Message {message_id} not found or has no content")
                return ChunkResult([], 0)
            
            # Remove existing chunks if any
            existing_chunks = session.query(Chunk).filter(Chunk.message_id == message_id).all()
            if existing_chunks:
                logger.info(f"Removing {len(existing_chunks)} existing chunks for message {message_id}")
                for chunk in existing_chunks:
                    session.delete(chunk)
            
            # Create chunks using the appropriate strategy
            chunks = []
            
            if options.chunk_type == ChunkType.PARAGRAPH:
                chunks = Chunker._chunk_by_paragraph(message, session)
            elif options.chunk_type == ChunkType.SENTENCE:
                chunks = Chunker._chunk_by_sentence(message, session)
            elif options.chunk_type == ChunkType.FIXED_LENGTH:
                chunks = Chunker._chunk_by_fixed_length(
                    message, session, options.chunk_size, options.chunk_overlap
                )
            elif options.chunk_type == ChunkType.TOKEN:
                chunks = Chunker._chunk_by_token(message, session, options.chunk_size)
            elif options.chunk_type == ChunkType.CUSTOM:
                if not options.separator:
                    logger.warning("Custom chunking requires a separator")
                    return ChunkResult([], 0)
                chunks = Chunker._chunk_by_custom(
                    message, session, options.separator, options.keep_separator
                )
            
            # Commit chunks to database
            session.commit()
            
            # Return result
            return ChunkResult(
                chunks=chunks,
                count=len(chunks),
                metadata={
                    "message_id": str(message_id),
                    "chunk_type": options.chunk_type,
                    "source_length": len(message.content)
                }
            )
    
    @staticmethod
    def chunk_text(
        text: str,
        options: ChunkerOptions = None,
        source_id: Union[uuid.UUID, str] = None,
        save_to_db: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Create chunks from arbitrary text.
        
        Args:
            text: Text content to chunk
            options: Chunking options
            source_id: Optional ID of the source (for tracking)
            save_to_db: Whether to save chunks to the database
            
        Returns:
            List of chunk dictionaries
        """
        options = options or ChunkerOptions()
        
        # Extract chunks using the appropriate strategy
        chunks = []
        
        if options.chunk_type == ChunkType.PARAGRAPH:
            chunks = Chunker._extract_paragraphs(text)
        elif options.chunk_type == ChunkType.SENTENCE:
            chunks = Chunker._extract_sentences(text)
        elif options.chunk_type == ChunkType.FIXED_LENGTH:
            chunks = Chunker._extract_fixed_length(
                text, options.chunk_size, options.chunk_overlap
            )
        elif options.chunk_type == ChunkType.TOKEN:
            chunks = Chunker._extract_tokens(text, options.chunk_size)
        elif options.chunk_type == ChunkType.CUSTOM:
            if not options.separator:
                logger.warning("Custom chunking requires a separator")
                return []
            chunks = Chunker._extract_custom(text, options.separator, options.keep_separator)
        
        # Convert to dictionaries
        chunk_dicts = [
            {
                "content": chunk_text,
                "position": i,
                "start_char": chunk_start,
                "end_char": chunk_end,
                "chunk_type": options.chunk_type
            }
            for i, (chunk_text, chunk_start, chunk_end) in enumerate(chunks)
        ]
        
        # Save to database if requested
        if save_to_db and source_id:
            with get_session() as session:
                # Create and save chunk objects
                for chunk_dict in chunk_dicts:
                    chunk = Chunk(
                        message_id=source_id if isinstance(source_id, uuid.UUID) else None,
                        content=chunk_dict["content"],
                        chunk_type=chunk_dict["chunk_type"],
                        position=chunk_dict["position"],
                        start_char=chunk_dict["start_char"],
                        end_char=chunk_dict["end_char"],
                        meta_info={
                            "source_id": str(source_id),
                            "source_type": "message" if isinstance(source_id, uuid.UUID) else "external"
                        }
                    )
                    session.add(chunk)
                session.commit()
        
        return chunk_dicts
    
    @staticmethod
    def _chunk_by_paragraph(message: Message, session) -> List[Chunk]:
        """
        Create paragraph-based chunks from a message.
        
        Args:
            message: Message to chunk
            session: Database session
            
        Returns:
            List of created Chunk instances
        """
        paragraphs = Chunker._extract_paragraphs(message.content)
        
        # Create chunk objects
        chunks = []
        for i, (paragraph_text, start_char, end_char) in enumerate(paragraphs):
            chunk = Chunk(
                message_id=message.id,
                content=paragraph_text,
                chunk_type=ChunkType.PARAGRAPH,
                position=i,
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now()
            )
            session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def _chunk_by_sentence(message: Message, session) -> List[Chunk]:
        """
        Create sentence-based chunks from a message.
        
        Args:
            message: Message to chunk
            session: Database session
            
        Returns:
            List of created Chunk instances
        """
        sentences = Chunker._extract_sentences(message.content)
        
        # Create chunk objects
        chunks = []
        for i, (sentence_text, start_char, end_char) in enumerate(sentences):
            chunk = Chunk(
                message_id=message.id,
                content=sentence_text,
                chunk_type=ChunkType.SENTENCE,
                position=i,
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now()
            )
            session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def _chunk_by_fixed_length(
        message: Message, session, chunk_size: int, chunk_overlap: int
    ) -> List[Chunk]:
        """
        Create fixed-length chunks from a message.
        
        Args:
            message: Message to chunk
            session: Database session
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between chunks
            
        Returns:
            List of created Chunk instances
        """
        fixed_chunks = Chunker._extract_fixed_length(
            message.content, chunk_size, chunk_overlap
        )
        
        # Create chunk objects
        chunks = []
        for i, (chunk_text, start_char, end_char) in enumerate(fixed_chunks):
            chunk = Chunk(
                message_id=message.id,
                content=chunk_text,
                chunk_type=ChunkType.FIXED_LENGTH,
                position=i,
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now(),
                meta_info={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap
                }
            )
            session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def _chunk_by_token(message: Message, session, token_size: int) -> List[Chunk]:
        """
        Create token-based chunks from a message.
        
        Args:
            message: Message to chunk
            session: Database session
            token_size: Approximate number of tokens per chunk
            
        Returns:
            List of created Chunk instances
        """
        tokens = Chunker._extract_tokens(message.content, token_size)
        
        # Create chunk objects
        chunks = []
        for i, (token_text, start_char, end_char) in enumerate(tokens):
            chunk = Chunk(
                message_id=message.id,
                content=token_text,
                chunk_type=ChunkType.TOKEN,
                position=i,
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now(),
                meta_info={
                    "target_token_size": token_size
                }
            )
            session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def _chunk_by_custom(message: Message, session, separator: str, keep_separator: bool) -> List[Chunk]:
        """
        Create custom chunks from a message using a separator.
        
        Args:
            message: Message to chunk
            session: Database session
            separator: String used to separate chunks
            keep_separator: Whether to keep separators in chunks
            
        Returns:
            List of created Chunk instances
        """
        custom_chunks = Chunker._extract_custom(
            message.content, separator, keep_separator
        )
        
        # Create chunk objects
        chunks = []
        for i, (chunk_text, start_char, end_char) in enumerate(custom_chunks):
            chunk = Chunk(
                message_id=message.id,
                content=chunk_text,
                chunk_type=ChunkType.CUSTOM,
                position=i,
                start_char=start_char,
                end_char=end_char,
                created_at=datetime.now(),
                meta_info={
                    "separator": separator,
                    "keep_separator": keep_separator
                }
            )
            session.add(chunk)
            chunks.append(chunk)
        
        return chunks
    
    @staticmethod
    def _extract_paragraphs(text: str) -> List[Tuple[str, int, int]]:
        """
        Extract paragraphs from text.
        
        Args:
            text: Text to extract paragraphs from
            
        Returns:
            List of tuples (paragraph_text, start_char, end_char)
        """
        if not text:
            return []
        
        # Split by double newlines to separate paragraphs
        pattern = r'\n\s*\n'
        splits = list(re.finditer(pattern, text))
        
        # Extract paragraphs
        paragraphs = []
        
        # Handle first paragraph
        if splits:
            first_split_pos = splits[0].start()
            first_para = text[:first_split_pos].strip()
            if first_para:
                paragraphs.append((first_para, 0, first_split_pos))
        else:
            # Only one paragraph
            paragraphs.append((text.strip(), 0, len(text)))
            return paragraphs
        
        # Middle paragraphs
        for i in range(len(splits) - 1):
            start = splits[i].end()
            end = splits[i + 1].start()
            para = text[start:end].strip()
            if para:
                paragraphs.append((para, start, end))
        
        # Last paragraph
        if splits:
            last_start = splits[-1].end()
            last_para = text[last_start:].strip()
            if last_para:
                paragraphs.append((last_para, last_start, len(text)))
        
        return paragraphs
    
    @staticmethod
    def _extract_sentences(text: str) -> List[Tuple[str, int, int]]:
        """
        Extract sentences from text.
        
        Args:
            text: Text to extract sentences from
            
        Returns:
            List of tuples (sentence_text, start_char, end_char)
        """
        if not text:
            return []
        
        # Simple sentence splitter pattern
        # This is a simplified approach and may need to be improved
        pattern = r'(?<=[.!?])\s+'
        splits = list(re.finditer(pattern, text))
        
        # Extract sentences
        sentences = []
        
        # Handle first sentence
        if splits:
            first_split_pos = splits[0].start()
            first_sentence = text[:first_split_pos + 1].strip()  # Include the period
            if first_sentence:
                sentences.append((first_sentence, 0, first_split_pos + 1))
        else:
            # Only one sentence
            sentences.append((text.strip(), 0, len(text)))
            return sentences
        
        # Middle sentences
        for i in range(len(splits) - 1):
            start = splits[i].end()
            end = splits[i + 1].start() + 1  # Include the period
            sentence = text[start:end].strip()
            if sentence:
                sentences.append((sentence, start, end))
        
        # Last sentence
        if splits:
            last_start = splits[-1].end()
            last_sentence = text[last_start:].strip()
            if last_sentence:
                sentences.append((last_sentence, last_start, len(text)))
        
        return sentences
    
    @staticmethod
    def _extract_fixed_length(text: str, chunk_size: int, overlap: int) -> List[Tuple[str, int, int]]:
        """
        Extract fixed-length chunks from text.
        
        Args:
            text: Text to extract chunks from
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            
        Returns:
            List of tuples (chunk_text, start_char, end_char)
        """
        if not text:
            return []
        
        if chunk_size <= overlap:
            raise ValueError("Chunk size must be greater than overlap")
        
        # Calculate step size
        step = chunk_size - overlap
        
        # Extract chunks
        chunks = []
        for i in range(0, len(text), step):
            chunk_text = text[i:i + chunk_size]
            if chunk_text:
                chunks.append((chunk_text, i, min(i + chunk_size, len(text))))
        
        return chunks
    
    @staticmethod
    def _extract_tokens(text: str, token_size: int) -> List[Tuple[str, int, int]]:
        """
        Extract token-based chunks from text.
        
        Args:
            text: Text to extract chunks from
            token_size: Approximate number of tokens per chunk
            
        Returns:
            List of tuples (chunk_text, start_char, end_char)
        """
        if not text:
            return []
        
        # Simple tokenization by whitespace
        # For a more accurate approach, use a proper tokenizer
        words = text.split()
        
        # Estimate word:token ratio as 0.75
        words_per_chunk = int(token_size * 0.75)
        
        # Extract chunks
        chunks = []
        text_pos = 0
        
        for i in range(0, len(words), words_per_chunk):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = ' '.join(chunk_words)
            
            # Find the position in the original text
            chunk_start = text.find(chunk_words[0], text_pos)
            chunk_end = chunk_start + len(chunk_text)
            text_pos = chunk_end
            
            chunks.append((chunk_text, chunk_start, chunk_end))
        
        return chunks
    
    @staticmethod
    def _extract_custom(text: str, separator: str, keep_separator: bool) -> List[Tuple[str, int, int]]:
        """
        Extract custom chunks using a separator.
        
        Args:
            text: Text to extract chunks from
            separator: String used to separate chunks
            keep_separator: Whether to keep separators in chunks
            
        Returns:
            List of tuples (chunk_text, start_char, end_char)
        """
        if not text:
            return []
        
        # Find all occurrences of the separator
        splits = list(re.finditer(re.escape(separator), text))
        
        # Extract chunks
        chunks = []
        
        # Handle first chunk
        if splits:
            first_split_pos = splits[0].start()
            first_chunk = text[:first_split_pos]
            if first_chunk:
                chunks.append((first_chunk, 0, first_split_pos))
        else:
            # No separators found
            chunks.append((text, 0, len(text)))
            return chunks
        
        # Middle chunks
        for i in range(len(splits) - 1):
            start = splits[i].end() if not keep_separator else splits[i].start()
            end = splits[i + 1].start()
            
            if keep_separator and i == 0:
                # Include the separator for the first chunk if keep_separator is True
                start = splits[i].start()
            
            chunk = text[start:end]
            if chunk:
                chunks.append((chunk, start, end))
        
        # Last chunk
        if splits:
            last_start = splits[-1].end() if not keep_separator else splits[-1].start()
            last_chunk = text[last_start:]
            if last_chunk:
                chunks.append((last_chunk, last_start, len(text)))
        
        return chunks