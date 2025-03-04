"""
Schemas for the unified search system.

This module defines the data models for search criteria and results across
multiple entity types in the carchive system, enabling consistent search
behavior across CLI, API, and GUI interfaces.
"""

from enum import Enum
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field


class SearchMode(str, Enum):
    """Search modes for text matching."""
    SUBSTRING = "substring"       # Simple substring search (default)
    EXACT = "exact"               # Exact match
    ANY_WORD = "any_word"         # Match if any word in the query is found
    ALL_WORDS = "all_words"       # Match if all words in the query are found (any order)
    REGEX = "regex"               # Use regular expression pattern


class EntityType(str, Enum):
    """Entity types that can be searched."""
    MESSAGE = "message"
    CONVERSATION = "conversation"
    CHUNK = "chunk"
    GENCOM = "gencom"             # Agent output of type 'gencom'
    EMBEDDING = "embedding"
    # Media entity is now supported
    MEDIA = "media"
    ALL = "all"                   # Search across all supported entity types


class SortOrder(str, Enum):
    """Sort order for search results."""
    RELEVANCE = "relevance"      # Sort by relevance score
    DATE_DESC = "date_desc"      # Newest first
    DATE_ASC = "date_asc"        # Oldest first
    ALPHA_ASC = "alpha_asc"      # Alphabetical A-Z 
    ALPHA_DESC = "alpha_desc"    # Alphabetical Z-A


class DateRange(BaseModel):
    """Date range for filtering search results."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True


class VectorSearch(BaseModel):
    """Vector similarity search parameters."""
    query: str = Field(..., description="The text to convert to a vector for similarity search")
    threshold: float = Field(0.7, description="Minimum similarity score (0.0 to 1.0)")
    provider: Optional[str] = Field(None, description="Embedding provider to use")
    top_k: int = Field(100, description="Maximum number of vector results to consider")


class SearchCriteria(BaseModel):
    """
    Unified search criteria for all entity types.
    
    This model defines parameters for searching across all content types
    in the carchive system with consistent behavior.
    """
    # Text search
    text_query: Optional[str] = Field(None, description="Text to search for")
    search_mode: SearchMode = Field(SearchMode.SUBSTRING, description="How to match the text query")
    
    # Entity filters
    entity_types: List[EntityType] = Field([EntityType.ALL], description="Entity types to search")
    gencom_types: Optional[List[str]] = Field(None, description="Specific gencom output types to search (e.g., 'category')")
    
    # Role and provider filters
    roles: Optional[List[str]] = Field(None, description="Filter by message roles (e.g., 'user', 'assistant')")
    providers: Optional[List[str]] = Field(None, description="Filter by providers (e.g., 'claude', 'chatgpt')")
    
    # Date filtering
    date_range: Optional[DateRange] = Field(None, description="Filter by date range")
    days: Optional[int] = Field(None, description="Only return results from the last N days")
    
    # Vector search
    vector_search: Optional[VectorSearch] = Field(None, description="Vector similarity search parameters")
    
    # Pagination and sorting
    limit: int = Field(10, description="Maximum number of results to return")
    offset: int = Field(0, description="Number of results to skip (for pagination)")
    sort_by: SortOrder = Field(SortOrder.RELEVANCE, description="How to sort the search results")
    
    # Advanced filters
    conversation_id: Optional[str] = Field(None, description="Filter by conversation ID")
    tag_ids: Optional[List[str]] = Field(None, description="Filter by tag IDs")
    collection_ids: Optional[List[str]] = Field(None, description="Filter by collection IDs")
    
    # Custom filtering
    custom_filters: Optional[Dict[str, Any]] = Field(None, description="Additional entity-specific filters")
    
    class Config:
        use_enum_values = True


class SearchResult(BaseModel):
    """Individual search result item."""
    id: str
    entity_type: EntityType
    content: str
    relevance_score: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Type-specific fields
    conversation_id: Optional[str] = None
    role: Optional[str] = None
    title: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class SearchResults(BaseModel):
    """Container for search results."""
    results: List[SearchResult]
    total_count: int
    query_time_ms: float
    criteria: SearchCriteria