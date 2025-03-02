"""
Unified search manager for the carchive system.

This module implements a centralized search manager that can search across
multiple entity types with consistent behavior and query capabilities.
"""

import time
import logging
import re
from typing import Dict, List, Optional, Any, Tuple, Set, cast
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, func, text, desc, asc
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.expression import BinaryExpression

from carchive.database.session import get_session
from carchive.database.models import (
    Message, Conversation, Chunk, AgentOutput, Embedding, Provider, Media, MessageMedia
)
from carchive.search.unified.schemas import (
    SearchCriteria, SearchResult, SearchResults, SearchMode, EntityType, SortOrder
)

logger = logging.getLogger(__name__)


class SearchManager:
    """
    Manager for unified search across multiple entity types.
    
    This class provides a centralized way to search across messages, conversations,
    gencom outputs, embeddings, and other content with consistent behavior.
    """
    
    def __init__(self) -> None:
        """Initialize the search manager."""
        pass
    
    def search(self, criteria: SearchCriteria) -> SearchResults:
        """
        Execute a search based on the provided criteria.
        
        Args:
            criteria: The search criteria to use
            
        Returns:
            SearchResults object containing the search results
        """
        start_time = time.time()
        all_results: List[SearchResult] = []
        total_count = 0
        
        # Determine which entity types to search
        entity_types_to_search = self._get_entity_types_to_search(criteria.entity_types)
        
        # Search each entity type
        with get_session() as session:
            for entity_type in entity_types_to_search:
                results, count = self._search_entity_type(session, entity_type, criteria)
                all_results.extend(results)
                total_count += count
        
        # Sort combined results if needed
        if len(entity_types_to_search) > 1:
            all_results = self._sort_combined_results(all_results, criteria.sort_by)
        
        # Apply pagination
        paginated_results = all_results[criteria.offset:criteria.offset + criteria.limit]
        
        # Calculate query time
        query_time_ms = (time.time() - start_time) * 1000
        
        return SearchResults(
            results=paginated_results,
            total_count=total_count,
            query_time_ms=query_time_ms,
            criteria=criteria
        )
    
    def _get_entity_types_to_search(self, entity_types: List[EntityType]) -> Set[EntityType]:
        """
        Determine which entity types to search based on the requested types.
        
        Args:
            entity_types: List of entity types from the search criteria
            
        Returns:
            Set of entity types to search
        """
        if EntityType.ALL in entity_types:
            # Search all supported entity types
            return {
                EntityType.MESSAGE,
                EntityType.CONVERSATION, 
                EntityType.CHUNK,
                EntityType.GENCOM,
                EntityType.MEDIA
            }
        else:
            # Search only the requested entity types
            return set(entity_types)
    
    def _search_entity_type(
        self, 
        session: Session, 
        entity_type: EntityType, 
        criteria: SearchCriteria
    ) -> Tuple[List[SearchResult], int]:
        """
        Search a specific entity type with the given criteria.
        
        Args:
            session: Database session
            entity_type: Entity type to search
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        if entity_type == EntityType.MESSAGE:
            return self._search_messages(session, criteria)
        elif entity_type == EntityType.CONVERSATION:
            return self._search_conversations(session, criteria)
        elif entity_type == EntityType.CHUNK:
            return self._search_chunks(session, criteria)
        elif entity_type == EntityType.GENCOM:
            return self._search_gencom(session, criteria)
        elif entity_type == EntityType.MEDIA:
            return self._search_media(session, criteria)
        else:
            logger.warning(f"Unsupported entity type for search: {entity_type}")
            return [], 0
    
    def _build_text_search_condition(
        self,
        column,
        text_query: str,
        search_mode: SearchMode
    ) -> BinaryExpression:
        """
        Build a SQLAlchemy condition for text search based on the search mode.
        
        Args:
            column: SQLAlchemy column to search
            text_query: Text to search for
            search_mode: How to match the text
            
        Returns:
            SQLAlchemy binary expression for the search condition
        """
        if not text_query:
            # Return a condition that always evaluates to true if no text query
            return column == column
            
        if search_mode == SearchMode.EXACT:
            return column == text_query
            
        elif search_mode == SearchMode.ANY_WORD:
            # Match if any word in the query is found
            words = [word.strip() for word in text_query.split() if word.strip()]
            if not words:
                return column.ilike(f"%{text_query}%")
                
            word_conditions = [column.ilike(f"%{word}%") for word in words]
            return or_(*word_conditions)
            
        elif search_mode == SearchMode.ALL_WORDS:
            # Match if all words in the query are found (in any order)
            words = [word.strip() for word in text_query.split() if word.strip()]
            if not words:
                return column.ilike(f"%{text_query}%")
                
            # Use PostgreSQL's regex capabilities for word boundary matching
            regex_parts = [f"(?=.*\\b{re.escape(word)}\\b)" for word in words]
            regex_pattern = "".join(regex_parts) + ".*"
            return column.op("~*")(regex_pattern)  # Case-insensitive regex
            
        elif search_mode == SearchMode.REGEX:
            # Use the query directly as a regex pattern
            return column.op("~*")(text_query)  # Case-insensitive regex
            
        else:  # Default to substring search
            return column.ilike(f"%{text_query}%")
    
    def _apply_common_filters(self, query: Query, criteria: SearchCriteria, model) -> Query:
        """
        Apply filters common to multiple entity types.
        
        Args:
            query: SQLAlchemy query object
            criteria: Search criteria
            model: SQLAlchemy model class
            
        Returns:
            Updated SQLAlchemy query
        """
        # Apply date filtering
        if hasattr(model, 'created_at'):
            if criteria.days is not None:
                date_filter = datetime.now() - timedelta(days=criteria.days)
                query = query.filter(model.created_at >= date_filter)
                
            if criteria.date_range is not None:
                if criteria.date_range.start:
                    query = query.filter(model.created_at >= criteria.date_range.start)
                if criteria.date_range.end:
                    query = query.filter(model.created_at <= criteria.date_range.end)
        
        # Apply conversation ID filter if applicable
        if criteria.conversation_id and hasattr(model, 'conversation_id'):
            query = query.filter(model.conversation_id == criteria.conversation_id)
            
        return query
    
    def _apply_sorting(self, query: Query, sort_by: SortOrder, model) -> Query:
        """
        Apply sorting to a query.
        
        Args:
            query: SQLAlchemy query object
            sort_by: Sort order
            model: SQLAlchemy model class
            
        Returns:
            Updated SQLAlchemy query
        """
        if sort_by == SortOrder.DATE_DESC and hasattr(model, 'created_at'):
            return query.order_by(desc(model.created_at))
        elif sort_by == SortOrder.DATE_ASC and hasattr(model, 'created_at'):
            return query.order_by(asc(model.created_at))
        elif sort_by == SortOrder.ALPHA_ASC and hasattr(model, 'content'):
            return query.order_by(asc(model.content))
        elif sort_by == SortOrder.ALPHA_DESC and hasattr(model, 'content'):
            return query.order_by(desc(model.content))
        else:
            # Default sort (usually by created_at desc)
            if hasattr(model, 'created_at'):
                return query.order_by(desc(model.created_at))
            return query
    
    def _search_messages(self, session: Session, criteria: SearchCriteria) -> Tuple[List[SearchResult], int]:
        """
        Search messages based on criteria.
        
        Args:
            session: Database session
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        # Start with base query
        query = session.query(Message)
        
        # Apply text search if specified
        if criteria.text_query:
            text_condition = self._build_text_search_condition(
                Message.content, 
                criteria.text_query,
                criteria.search_mode
            )
            query = query.filter(text_condition)
        
        # Apply role filters
        if criteria.roles:
            query = query.filter(Message.role.in_([r.lower() for r in criteria.roles]))
        
        # Apply provider filters
        if criteria.providers:
            provider_ids = self._get_provider_ids(session, criteria.providers)
            if provider_ids:
                query = query.join(
                    Conversation, 
                    Message.conversation_id == Conversation.id
                ).filter(Conversation.provider_id.in_(provider_ids))
        
        # Apply common filters
        query = self._apply_common_filters(query, criteria, Message)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        query = self._apply_sorting(query, criteria.sort_by, Message)
        
        # Apply pagination if not combining results
        if EntityType.MESSAGE in criteria.entity_types and EntityType.ALL not in criteria.entity_types:
            query = query.offset(criteria.offset).limit(criteria.limit)
        
        # Execute query and convert to results
        results = []
        for message in query.all():
            results.append(SearchResult(
                id=str(message.id),
                entity_type=EntityType.MESSAGE,
                content=message.content or "",
                relevance_score=1.0,  # No relevance score for basic search
                created_at=message.created_at,
                updated_at=message.updated_at,
                conversation_id=str(message.conversation_id) if message.conversation_id else None,
                role=message.role,
                metadata={
                    "parent_id": str(message.parent_id) if message.parent_id else None,
                    "index": message.index
                }
            ))
        
        return results, total_count
    
    def _search_conversations(self, session: Session, criteria: SearchCriteria) -> Tuple[List[SearchResult], int]:
        """
        Search conversations based on criteria.
        
        Args:
            session: Database session
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        # Start with base query
        query = session.query(Conversation)
        
        # Apply text search if specified
        if criteria.text_query:
            # Search in title and meta_info
            title_condition = self._build_text_search_condition(
                Conversation.title, 
                criteria.text_query,
                criteria.search_mode
            )
            # For meta_info, we need to handle JSON field
            if criteria.search_mode == SearchMode.SUBSTRING:
                # Simple case - just convert to string and search
                meta_info_condition = cast(Conversation.meta_info, String).ilike(f"%{criteria.text_query}%")
            else:
                # For other modes, this is more complex - might need raw SQL
                # For now, we'll just use the title search
                meta_info_condition = title_condition
                
            query = query.filter(or_(title_condition, meta_info_condition))
        
        # Apply provider filters
        if criteria.providers:
            provider_ids = self._get_provider_ids(session, criteria.providers)
            if provider_ids:
                query = query.filter(Conversation.provider_id.in_(provider_ids))
        
        # Apply common filters
        query = self._apply_common_filters(query, criteria, Conversation)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        query = self._apply_sorting(query, criteria.sort_by, Conversation)
        
        # Apply pagination if not combining results
        if EntityType.CONVERSATION in criteria.entity_types and EntityType.ALL not in criteria.entity_types:
            query = query.offset(criteria.offset).limit(criteria.limit)
        
        # Execute query and convert to results
        results = []
        for conversation in query.all():
            results.append(SearchResult(
                id=str(conversation.id),
                entity_type=EntityType.CONVERSATION,
                content=conversation.title or "",
                relevance_score=1.0,  # No relevance score for basic search
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                title=conversation.title,
                metadata={
                    "provider_id": str(conversation.provider_id) if conversation.provider_id else None,
                    "meta_info": conversation.meta_info
                }
            ))
        
        return results, total_count
    
    def _search_chunks(self, session: Session, criteria: SearchCriteria) -> Tuple[List[SearchResult], int]:
        """
        Search chunks based on criteria.
        
        Args:
            session: Database session
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        # Start with base query
        query = session.query(Chunk)
        
        # Apply text search if specified
        if criteria.text_query:
            text_condition = self._build_text_search_condition(
                Chunk.content, 
                criteria.text_query,
                criteria.search_mode
            )
            query = query.filter(text_condition)
        
        # Apply role filters via message join
        if criteria.roles:
            query = query.join(
                Message, 
                Chunk.message_id == Message.id
            ).filter(Message.role.in_([r.lower() for r in criteria.roles]))
        
        # Apply provider filters
        if criteria.providers:
            provider_ids = self._get_provider_ids(session, criteria.providers)
            if provider_ids:
                query = query.join(
                    Message, 
                    Chunk.message_id == Message.id
                ).join(
                    Conversation, 
                    Message.conversation_id == Conversation.id
                ).filter(Conversation.provider_id.in_(provider_ids))
        
        # Apply common filters
        query = self._apply_common_filters(query, criteria, Chunk)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        query = self._apply_sorting(query, criteria.sort_by, Chunk)
        
        # Apply pagination if not combining results
        if EntityType.CHUNK in criteria.entity_types and EntityType.ALL not in criteria.entity_types:
            query = query.offset(criteria.offset).limit(criteria.limit)
        
        # Execute query and convert to results
        results = []
        for chunk in query.all():
            # Get message and conversation information
            message = None
            conversation_id = None
            role = None
            
            if chunk.message_id:
                message = session.query(Message).filter_by(id=chunk.message_id).first()
                if message:
                    conversation_id = message.conversation_id
                    role = message.role
            
            results.append(SearchResult(
                id=str(chunk.id),
                entity_type=EntityType.CHUNK,
                content=chunk.content or "",
                relevance_score=1.0,  # No relevance score for basic search
                created_at=chunk.created_at,
                updated_at=chunk.updated_at,
                conversation_id=str(conversation_id) if conversation_id else None,
                role=role,
                metadata={
                    "message_id": str(chunk.message_id) if chunk.message_id else None,
                    "index": chunk.index
                }
            ))
        
        return results, total_count
    
    def _search_gencom(self, session: Session, criteria: SearchCriteria) -> Tuple[List[SearchResult], int]:
        """
        Search gencom outputs based on criteria.
        
        Args:
            session: Database session
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        # Start with base query for agent outputs of gencom type
        base_query = session.query(AgentOutput).filter(
            AgentOutput.output_type.like("gencom%")
        )
        
        # Filter by specific gencom types if specified
        if criteria.gencom_types:
            gencom_type_conditions = []
            for gencom_type in criteria.gencom_types:
                if gencom_type == "gencom":
                    gencom_type_conditions.append(AgentOutput.output_type == "gencom")
                else:
                    gencom_type_conditions.append(AgentOutput.output_type == f"gencom_{gencom_type}")
            base_query = base_query.filter(or_(*gencom_type_conditions))
        
        # Apply text search if specified
        if criteria.text_query:
            text_condition = self._build_text_search_condition(
                AgentOutput.content, 
                criteria.text_query,
                criteria.search_mode
            )
            base_query = base_query.filter(text_condition)
        
        # Apply role filters (only for message targets)
        if criteria.roles:
            role_conditions = []
            
            # For message targets, filter by role
            message_ids = session.query(Message.id).filter(
                Message.role.in_([r.lower() for r in criteria.roles])
            ).subquery()
            
            role_conditions.append(
                and_(
                    AgentOutput.target_type == "message",
                    AgentOutput.target_id.in_(message_ids)
                )
            )
            
            # Add conditions for non-message targets (they don't have roles)
            role_conditions.append(AgentOutput.target_type != "message")
            
            base_query = base_query.filter(or_(*role_conditions))
        
        # Apply provider filters
        if criteria.providers:
            provider_ids = self._get_provider_ids(session, criteria.providers)
            if provider_ids:
                provider_conditions = []
                
                # For message targets
                message_query = session.query(Message.id).join(
                    Conversation, 
                    Message.conversation_id == Conversation.id
                ).filter(
                    Conversation.provider_id.in_(provider_ids)
                ).subquery()
                
                provider_conditions.append(
                    and_(
                        AgentOutput.target_type == "message",
                        AgentOutput.target_id.in_(message_query)
                    )
                )
                
                # For conversation targets
                conversation_query = session.query(Conversation.id).filter(
                    Conversation.provider_id.in_(provider_ids)
                ).subquery()
                
                provider_conditions.append(
                    and_(
                        AgentOutput.target_type == "conversation",
                        AgentOutput.target_id.in_(conversation_query)
                    )
                )
                
                # Combine all provider conditions
                base_query = base_query.filter(or_(*provider_conditions))
        
        # Apply common filters
        base_query = self._apply_common_filters(base_query, criteria, AgentOutput)
        
        # Get total count before pagination
        total_count = base_query.count()
        
        # Apply sorting
        query = self._apply_sorting(base_query, criteria.sort_by, AgentOutput)
        
        # Apply pagination if not combining results
        if EntityType.GENCOM in criteria.entity_types and EntityType.ALL not in criteria.entity_types:
            query = query.offset(criteria.offset).limit(criteria.limit)
        
        # Execute query and convert to results
        results = []
        for agent_output in query.all():
            # Get target information
            target_obj = None
            conversation_id = None
            role = None
            
            if agent_output.target_type == "message":
                target_obj = session.query(Message).filter_by(id=agent_output.target_id).first()
                if target_obj:
                    conversation_id = target_obj.conversation_id
                    role = target_obj.role
            elif agent_output.target_type == "conversation":
                target_obj = session.query(Conversation).filter_by(id=agent_output.target_id).first()
                if target_obj:
                    conversation_id = target_obj.id
            
            results.append(SearchResult(
                id=str(agent_output.id),
                entity_type=EntityType.GENCOM,
                content=agent_output.content or "",
                relevance_score=1.0,  # No relevance score for basic search
                created_at=agent_output.created_at,
                conversation_id=str(conversation_id) if conversation_id else None,
                role=role,
                metadata={
                    "output_type": agent_output.output_type,
                    "target_type": agent_output.target_type,
                    "target_id": agent_output.target_id
                }
            ))
        
        return results, total_count
    
    def _search_media(self, session: Session, criteria: SearchCriteria) -> Tuple[List[SearchResult], int]:
        """
        Search media based on criteria.
        
        Args:
            session: Database session
            criteria: Search criteria
            
        Returns:
            Tuple of (list of search results, total count)
        """
        # Start with base query
        query = session.query(Media)
        
        # Apply text search if specified
        if criteria.text_query:
            # Search in filename, media_type, description
            filename_condition = self._build_text_search_condition(
                Media.filename, 
                criteria.text_query,
                criteria.search_mode
            )
            media_type_condition = self._build_text_search_condition(
                Media.media_type, 
                criteria.text_query,
                criteria.search_mode
            )
            description_condition = self._build_text_search_condition(
                Media.description, 
                criteria.text_query,
                criteria.search_mode
            )
            
            query = query.filter(or_(
                filename_condition, 
                media_type_condition,
                description_condition
            ))
        
        # Apply role filters via MessageMedia and Message joins
        if criteria.roles:
            role_message_ids = session.query(Message.id).filter(
                Message.role.in_([r.lower() for r in criteria.roles])
            ).subquery()
            
            media_ids = session.query(MessageMedia.media_id).filter(
                MessageMedia.message_id.in_(role_message_ids)
            ).subquery()
            
            query = query.filter(Media.id.in_(media_ids))
        
        # Apply provider filters
        if criteria.providers:
            provider_ids = self._get_provider_ids(session, criteria.providers)
            if provider_ids:
                # This requires multiple joins: Media -> MediaMessage -> Message -> Conversation
                provider_message_ids = session.query(Message.id).join(
                    Conversation, 
                    Message.conversation_id == Conversation.id
                ).filter(
                    Conversation.provider_id.in_(provider_ids)
                ).subquery()
                
                provider_media_ids = session.query(MessageMedia.media_id).filter(
                    MessageMedia.message_id.in_(provider_message_ids)
                ).subquery()
                
                query = query.filter(Media.id.in_(provider_media_ids))
        
        # Apply common filters
        query = self._apply_common_filters(query, criteria, Media)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply sorting
        query = self._apply_sorting(query, criteria.sort_by, Media)
        
        # Apply pagination if not combining results
        if EntityType.MEDIA in criteria.entity_types and EntityType.ALL not in criteria.entity_types:
            query = query.offset(criteria.offset).limit(criteria.limit)
        
        # Execute query and convert to results
        results = []
        for media in query.all():
            # Get associated message and conversation
            message_id = None
            conversation_id = None
            role = None
            
            # Find first linked message (if any)
            media_message = session.query(MessageMedia).filter_by(media_id=media.id).first()
            if media_message:
                message_id = media_message.message_id
                message = session.query(Message).filter_by(id=message_id).first()
                if message:
                    conversation_id = message.conversation_id
                    role = message.role
            
            results.append(SearchResult(
                id=str(media.id),
                entity_type=EntityType.MEDIA,
                content=media.description or media.filename or "",
                relevance_score=1.0,  # No relevance score for basic search
                created_at=media.created_at,
                updated_at=media.updated_at,
                conversation_id=str(conversation_id) if conversation_id else None,
                role=role,
                metadata={
                    "filename": media.filename,
                    "media_type": media.media_type,
                    "file_size": media.file_size,
                    "width": media.width,
                    "height": media.height,
                    "message_id": str(message_id) if message_id else None
                }
            ))
        
        return results, total_count
    
    def _get_provider_ids(self, session: Session, provider_names: List[str]) -> List[str]:
        """
        Get provider IDs from provider names.
        
        Args:
            session: Database session
            provider_names: List of provider names
            
        Returns:
            List of provider IDs
        """
        providers = session.query(Provider).filter(
            Provider.name.in_([p.lower() for p in provider_names])
        ).all()
        return [str(provider.id) for provider in providers]
    
    def _sort_combined_results(
        self, 
        results: List[SearchResult], 
        sort_by: SortOrder
    ) -> List[SearchResult]:
        """
        Sort combined results from multiple entity types.
        
        Args:
            results: List of search results
            sort_by: Sort order
            
        Returns:
            Sorted list of search results
        """
        if sort_by == SortOrder.DATE_DESC:
            return sorted(results, key=lambda r: r.created_at, reverse=True)
        elif sort_by == SortOrder.DATE_ASC:
            return sorted(results, key=lambda r: r.created_at)
        elif sort_by == SortOrder.ALPHA_ASC:
            return sorted(results, key=lambda r: r.content)
        elif sort_by == SortOrder.ALPHA_DESC:
            return sorted(results, key=lambda r: r.content, reverse=True)
        else:
            # Default to date descending
            return sorted(results, key=lambda r: r.created_at, reverse=True)