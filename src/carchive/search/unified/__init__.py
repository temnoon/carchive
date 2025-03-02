"""
Unified search system for the carchive application.

This package provides a centralized search system that works across all entity types
(messages, conversations, gencom outputs, chunks, media, etc.) with consistent behavior.
"""

from carchive.search.unified.schemas import (
    SearchCriteria, SearchResult, SearchResults,
    SearchMode, EntityType, SortOrder, DateRange, VectorSearch
)
from carchive.search.unified.manager import SearchManager

__all__ = [
    'SearchManager',
    'SearchCriteria',
    'SearchResult',
    'SearchResults',
    'SearchMode',
    'EntityType',
    'SortOrder',
    'DateRange',
    'VectorSearch',
]