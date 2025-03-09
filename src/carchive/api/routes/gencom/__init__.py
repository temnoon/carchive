"""
GenCom routes for the carchive API.
Flask-based implementation following the architectural standards.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
import logging
from flask import Blueprint, request, jsonify

from carchive.pipelines.content_tasks import ContentTaskManager
from carchive.database.session import get_session
from carchive.database.models import Message, Conversation, Chunk, AgentOutput, Provider
from sqlalchemy import func, desc, text

# Configure logging
logger = logging.getLogger(__name__)

# Create blueprint
gencom_router = Blueprint('gencom_inner', __name__, url_prefix='/gencom')

# Request and response models (Pydantic-based)
class GencomRequest(BaseModel):
    target_type: str = Field(..., description="Type of target: 'message', 'conversation', 'chunk'")
    target_id: UUID = Field(..., description="ID of the target item")
    output_type: str = Field("gencom", description="Output type (e.g., 'gencom', 'gencom_summary', 'gencom_category')")
    provider: str = Field("ollama", description="Provider to use (e.g., 'ollama', 'openai', 'anthropic')")
    prompt_template: Optional[str] = Field(None, description="Custom prompt template with {content} placeholder")
    max_words: Optional[int] = Field(None, description="Maximum word count for generated content")
    max_tokens: Optional[int] = Field(None, description="Maximum token count for generated content")
    override: bool = Field(False, description="Whether to override existing outputs")
    generate_embedding: bool = Field(False, description="Whether to generate embeddings for the output")
    embedding_provider: Optional[str] = Field(None, description="Provider to use for embeddings")

class GencomResponse(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    output_type: str
    content: str
    agent_name: str
    created_at: str
    
class BatchGencomRequest(BaseModel):
    target_type: str = Field(..., description="Type of target: 'message', 'conversation', 'chunk'")
    output_type: str = Field("gencom", description="Output type (e.g., 'gencom', 'gencom_summary', 'gencom_category')")
    provider: str = Field("ollama", description="Provider to use (e.g., 'ollama', 'openai', 'anthropic')")
    prompt_template: Optional[str] = Field(None, description="Custom prompt template with {content} placeholder")
    max_words: Optional[int] = Field(None, description="Maximum word count for generated content")
    max_tokens: Optional[int] = Field(None, description="Maximum token count for generated content")
    min_word_count: int = Field(5, description="Minimum word count for content to process")
    limit: Optional[int] = Field(None, description="Maximum number of items to process")
    roles: Optional[List[str]] = Field(None, description="For messages, filter by roles (e.g., ['assistant'])")
    source_provider: Optional[str] = Field(None, description="Filter by content provider")
    days: Optional[int] = Field(None, description="Only process content from the last N days")
    override: bool = Field(False, description="Whether to override existing outputs")
    generate_embedding: bool = Field(False, description="Whether to generate embeddings for output")
    embedding_provider: Optional[str] = Field(None, description="Provider to use for embeddings")

class BatchGencomResponse(BaseModel):
    processed: int
    failed: int
    skipped: int
    embedding_success: Optional[int] = None
    embedding_failed: Optional[int] = None
    
class GencomCategoryStats(BaseModel):
    category: str
    total: int
    role_counts: Optional[dict] = None
    
class GencomPurgeRequest(BaseModel):
    output_type: str = Field(..., description="Output type to purge (e.g., 'gencom_category')")
    target_type: str = Field("message", description="Target type to purge ('message', 'conversation', 'chunk')")
    conversation_id: Optional[UUID] = Field(None, description="Optional conversation ID to filter by")
    source_provider: Optional[str] = Field(None, description="Only purge outputs from this provider")
    role: Optional[str] = Field(None, description="Only purge outputs from messages with this role")

class GencomListResponse(BaseModel):
    id: UUID
    target_type: str
    target_id: UUID
    output_type: str
    content: str
    agent_name: str
    created_at: str
    target_content: Optional[str] = None

# API endpoints
def generate_comment(request_data):
    """Generate an AI comment for a specific content item"""
    try:
        # Create content task manager with specified provider
        manager = ContentTaskManager(provider=request_data.provider)
        
        # Run the task
        output = manager.run_task_for_target(
            target_type=request_data.target_type,
            target_id=str(request_data.target_id),
            task=request_data.output_type,
            prompt_template=request_data.prompt_template,
            override=request_data.override,
            max_words=request_data.max_words,
            max_tokens=request_data.max_tokens
        )
        
        # Generate embedding if requested
        if request_data.generate_embedding:
            from carchive.embeddings.embed_manager import EmbeddingManager
            embed_provider = request_data.embedding_provider or request_data.provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
            
            # Generate embedding for the gencom content
            embedding = embedding_manager.embed_texts(
                texts=[output.content],
                parent_ids=[str(output.id)],
                parent_type="agent_output"
            )
            logger.info(f"Generated embedding for comment (Embedding ID: {embedding[0].id})")
        
        # Return response
        return GencomResponse(
            id=output.id,
            target_type=output.target_type,
            target_id=output.target_id,
            output_type=output.output_type,
            content=output.content,
            agent_name=output.agent_name,
            created_at=output.created_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error generating comment: {str(e)}")
        raise Exception(str(e))

def batch_generate_comments(request_data):
    """Generate AI comments for multiple content items based on criteria"""
    try:
        # Create content task manager with specified provider
        manager = ContentTaskManager(provider=request_data.provider)
        
        # Initialize an embedding manager if needed
        embedding_manager = None
        if request_data.generate_embedding:
            from carchive.embeddings.embed_manager import EmbeddingManager
            embed_provider = request_data.embedding_provider or request_data.provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
        
        # Process based on target type and criteria
        with get_session() as session:
            # Get provider ID if source_provider is specified
            provider_id = None
            if request_data.source_provider:
                provider_obj = session.query(Provider).filter_by(name=request_data.source_provider.lower()).first()
                if not provider_obj:
                    raise Exception(f"Provider '{request_data.source_provider}' not found")
                provider_id = provider_obj.id
            
            # Get items to process based on target type and filters
            items_to_process = []
            
            if request_data.target_type == "message":
                # Build query for messages with word count filter
                word_count_expr = func.array_length(func.regexp_split_to_array(Message.content, r'\s+'), 1)
                base_query = session.query(Message).filter(Message.content.isnot(None))
                base_query = base_query.filter(word_count_expr >= request_data.min_word_count)
                
                # Apply role filter if specified
                if request_data.roles:
                    base_query = base_query.filter(Message.role.in_([r.lower() for r in request_data.roles]))
                
                # Apply provider filter if specified
                if provider_id:
                    base_query = base_query.join(Conversation, Message.conversation_id == Conversation.id)
                    base_query = base_query.filter(Conversation.provider_id == provider_id)
                
                # Apply date filter if specified
                if request_data.days:
                    date_filter = text(f"created_at > NOW() - INTERVAL '{request_data.days} days'")
                    base_query = base_query.filter(date_filter)
                    
                # Apply limit if specified
                if request_data.limit:
                    base_query = base_query.limit(request_data.limit)
                    
                items_to_process = base_query.all()
                
            elif request_data.target_type == "conversation":
                # Build query for conversations
                base_query = session.query(Conversation)
                
                # Apply provider filter if specified
                if provider_id:
                    base_query = base_query.filter(Conversation.provider_id == provider_id)
                
                # Apply date filter if specified
                if request_data.days:
                    date_filter = text(f"created_at > NOW() - INTERVAL '{request_data.days} days'")
                    base_query = base_query.filter(date_filter)
                    
                # Apply limit if specified
                if request_data.limit:
                    base_query = base_query.limit(request_data.limit)
                    
                items_to_process = base_query.all()
                
            elif request_data.target_type == "chunk":
                # Build query for chunks with word count filter
                word_count_expr = func.array_length(func.regexp_split_to_array(Chunk.content, r'\s+'), 1)
                base_query = session.query(Chunk).filter(Chunk.content.isnot(None))
                base_query = base_query.filter(word_count_expr >= request_data.min_word_count)
                
                # Apply provider filter if specified
                if provider_id:
                    base_query = base_query.join(Message, Chunk.message_id == Message.id)
                    base_query = base_query.join(Conversation, Message.conversation_id == Conversation.id)
                    base_query = base_query.filter(Conversation.provider_id == provider_id)
                
                # Apply date filter if specified
                if request_data.days:
                    date_filter = text(f"created_at > NOW() - INTERVAL '{request_data.days} days'")
                    base_query = base_query.filter(date_filter)
                    
                # Apply limit if specified
                if request_data.limit:
                    base_query = base_query.limit(request_data.limit)
                    
                items_to_process = base_query.all()
            
            else:
                raise Exception(f"Unsupported target type: {request_data.target_type}")
        
        # Process items
        processed = 0
        failed = 0
        skipped = 0
        embedding_success = 0
        embedding_failed = 0
        
        for item in items_to_process:
            try:
                # Check if an output already exists
                with get_session() as session:
                    existing = session.query(AgentOutput).filter(
                        AgentOutput.target_type == request_data.target_type,
                        AgentOutput.target_id == item.id,
                        AgentOutput.output_type == request_data.output_type
                    ).first()
                    
                    if existing and not request_data.override:
                        skipped += 1
                        continue
                
                # Generate comment
                output = manager.run_task_for_target(
                    target_type=request_data.target_type,
                    target_id=str(item.id),
                    task=request_data.output_type,
                    prompt_template=request_data.prompt_template,
                    override=request_data.override,
                    max_words=request_data.max_words,
                    max_tokens=request_data.max_tokens
                )
                
                processed += 1
                
                # Generate embedding if requested
                if request_data.generate_embedding and embedding_manager:
                    try:
                        embedding = embedding_manager.embed_texts(
                            texts=[output.content],
                            parent_ids=[str(output.id)],
                            parent_type="agent_output"
                        )
                        embedding_success += 1
                    except Exception as embed_err:
                        logger.error(f"Error generating embedding for output {output.id}: {embed_err}")
                        embedding_failed += 1
                
            except Exception as e:
                logger.error(f"Error processing {request_data.target_type} {item.id}: {e}")
                failed += 1
        
        # Return results
        response = BatchGencomResponse(
            processed=processed,
            failed=failed,
            skipped=skipped
        )
        
        if request_data.generate_embedding:
            response.embedding_success = embedding_success
            response.embedding_failed = embedding_failed
            
        return response
    
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}")
        raise Exception(str(e))

def purge_gencom(request_data):
    """Purge generated AI comments of a specific type"""
    try:
        with get_session() as session:
            # Start building the query
            query = session.query(AgentOutput).filter(
                AgentOutput.output_type == request_data.output_type
            )
            
            # First we need to build a query to get the IDs we want to delete
            target_ids_to_delete = set()
            
            # Apply filters based on what was specified
            if request_data.source_provider:
                # First get the provider ID
                provider = session.query(Provider).filter(
                    Provider.name == request_data.source_provider
                ).first()
                
                if not provider:
                    raise Exception(f"Provider '{request_data.source_provider}' not found")
                    
                provider_id = provider.id
            
            # Create queries to find targets that match our criteria
            if request_data.target_type == "message":
                # Start with a query to get message IDs
                message_query = session.query(Message.id)
                
                # Filter by role if needed
                if request_data.role:
                    message_query = message_query.filter(Message.role == request_data.role)
                
                # Add conversation-based filters
                if request_data.source_provider or request_data.conversation_id:
                    message_query = message_query.join(
                        Conversation,
                        Message.conversation_id == Conversation.id
                    )
                    
                    if request_data.source_provider:
                        message_query = message_query.filter(Conversation.provider_id == provider_id)
                    
                    if request_data.conversation_id:
                        message_query = message_query.filter(Message.conversation_id == request_data.conversation_id)
                
                # Get all message IDs that match criteria
                target_ids_to_delete = {str(row[0]) for row in message_query.all()}
                
            elif request_data.target_type == "conversation":
                # Start with a query to get conversation IDs
                conversation_query = session.query(Conversation.id)
                
                # Add filters
                if request_data.source_provider:
                    conversation_query = conversation_query.filter(Conversation.provider_id == provider_id)
                    
                if request_data.conversation_id:
                    conversation_query = conversation_query.filter(Conversation.id == request_data.conversation_id)
                    
                # Get all conversation IDs that match criteria
                target_ids_to_delete = {str(row[0]) for row in conversation_query.all()}
            
            # If there are no matching targets, quit early
            if not target_ids_to_delete:
                return {"message": f"No {request_data.target_type}s found matching the criteria", "deleted": 0}
            
            # Now get the count of agent outputs matching these targets
            count_query = session.query(func.count(AgentOutput.id)).filter(
                AgentOutput.output_type == request_data.output_type,
                AgentOutput.target_type == request_data.target_type,
                AgentOutput.target_id.in_(target_ids_to_delete)
            )
            
            count = count_query.scalar()
            
            if count == 0:
                return {"message": f"No {request_data.output_type} outputs found matching the criteria", "deleted": 0}
            
            # Delete matching outputs
            delete_query = session.query(AgentOutput).filter(
                AgentOutput.output_type == request_data.output_type,
                AgentOutput.target_type == request_data.target_type,
                AgentOutput.target_id.in_(target_ids_to_delete)
            )
            
            deleted = delete_query.delete(synchronize_session=False)
            session.commit()
            
            return {"message": f"Successfully deleted {deleted} {request_data.output_type} outputs", "deleted": deleted}
    
    except Exception as e:
        logger.error(f"Error purging gencom: {str(e)}")
        raise Exception(str(e))

def list_gencom(
    output_type="gencom",
    target_type=None,
    target_id=None,
    include_target_content=False,
    limit=50,
    offset=0
):
    """List AI-generated comments matching the criteria"""
    try:
        with get_session() as session:
            # Build base query
            query = session.query(AgentOutput).filter(
                AgentOutput.output_type == output_type
            )
            
            # Apply filters
            if target_type:
                query = query.filter(AgentOutput.target_type == target_type)
                
            if target_id:
                query = query.filter(AgentOutput.target_id == target_id)
                
            # Apply pagination
            query = query.order_by(AgentOutput.created_at.desc())
            query = query.offset(offset).limit(limit)
            
            results = query.all()
            
            # Prepare response
            response = []
            for result in results:
                item = {
                    "id": result.id,
                    "target_type": result.target_type,
                    "target_id": result.target_id,
                    "output_type": result.output_type,
                    "content": result.content,
                    "agent_name": result.agent_name,
                    "created_at": result.created_at.isoformat(),
                    "target_content": None
                }
                
                # Add target content if requested
                if include_target_content:
                    target_content = None
                    if result.target_type == "message":
                        message = session.query(Message).filter_by(id=result.target_id).first()
                        if message:
                            target_content = message.content
                    elif result.target_type == "conversation":
                        # For conversations, get title as content
                        conversation = session.query(Conversation).filter_by(id=result.target_id).first()
                        if conversation:
                            target_content = conversation.title
                    elif result.target_type == "chunk":
                        chunk = session.query(Chunk).filter_by(id=result.target_id).first()
                        if chunk:
                            target_content = chunk.content
                            
                    item["target_content"] = target_content
                
                response.append(GencomListResponse(**item))
                
            return response
    
    except Exception as e:
        logger.error(f"Error listing gencom: {str(e)}")
        raise Exception(str(e))

def list_categories(
    target_type="message",
    output_type="gencom_category",
    min_count=3,
    limit=20,
    exclude_generic=False,
    role=None
):
    """List and analyze gencom category statistics"""
    try:
        with get_session() as session:
            # Process based on target type
            if target_type == "message":
                # For messages, we can filter by role and include role stats
                query = session.query(
                    AgentOutput.content,
                    Message.role,
                    func.count(AgentOutput.id).label('count')
                ).join(
                    Message, 
                    AgentOutput.target_id == Message.id
                ).filter(
                    AgentOutput.output_type == output_type,
                    AgentOutput.target_type == target_type
                )
                
                # Apply role filter if specified
                if role:
                    query = query.filter(Message.role == role)
                
                # Group by both content and role
                query = query.group_by(
                    AgentOutput.content,
                    Message.role
                )
                
            else:
                # For other target types, we don't have role information
                query = session.query(
                    AgentOutput.content,
                    func.count(AgentOutput.id).label('count')
                ).filter(
                    AgentOutput.output_type == output_type,
                    AgentOutput.target_type == target_type
                )
                
                # Group by content only
                query = query.group_by(
                    AgentOutput.content
                )
            
            # Execute the query
            results = query.all()
            
            # Process results
            category_stats = {}
            for row in results:
                if target_type == "message":
                    content, msg_role, count = row
                    # Skip if role filter applied but doesn't match
                    if role and msg_role != role:
                        continue
                else:
                    content, count = row
                    msg_role = None
                
                # Extract primary category (first sentence or phrase)
                category = content.strip().split('.')[0].strip()
                
                # Skip empty or generic categories
                if not category or category.lower() in ['none', 'unknown', 'n/a']:
                    continue
                    
                # Skip generic "ready/waiting" categories if requested
                if exclude_generic:
                    generic_patterns = [
                        'ready', 'waiting', 'i don\'t see', 'no content', 'haven\'t provided',
                        'please provide', 'can\'t categorize', 'need more', 'need content',
                        'missing content', 'nothing to categorize'
                    ]
                    
                    # Check if any pattern appears in the category (case insensitive)
                    if any(pattern.lower() in category.lower() for pattern in generic_patterns):
                        continue
                    
                # Initialize nested dictionaries if needed
                if category not in category_stats:
                    category_stats[category] = {'total': 0, 'role_counts': {}}
                    
                # Update role-specific counts
                if target_type == "message" and msg_role:
                    if msg_role not in category_stats[category]['role_counts']:
                        category_stats[category]['role_counts'][msg_role] = 0
                    category_stats[category]['role_counts'][msg_role] += count
                
                # Update total count
                category_stats[category]['total'] += count
            
            # Filter by minimum count
            filtered_stats = {k: v for k, v in category_stats.items() if v['total'] >= min_count}
            
            # Sort by total occurrences (descending)
            sorted_stats = dict(sorted(filtered_stats.items(), key=lambda x: x[1]['total'], reverse=True))
            
            # Build response
            result = []
            for i, (category, stats) in enumerate(sorted_stats.items()):
                if i >= limit:
                    break
                
                result.append(GencomCategoryStats(
                    category=category,
                    total=stats['total'],
                    role_counts=stats.get('role_counts')
                ))
                
            return result
    
    except Exception as e:
        logger.error(f"Error analyzing categories: {str(e)}")
        raise Exception(str(e))