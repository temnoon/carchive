# src/carchive/cli/gencom_cli.py
import typer
import logging
import uuid
from typing import Optional, List
from sqlalchemy import func, String, cast, text
from sqlalchemy.dialects.postgresql import JSONB
from carchive.database.session import get_session
from carchive.database.models import Message, Conversation, Chunk, AgentOutput
from carchive.pipelines.content_tasks import ContentTaskManager
from carchive.embeddings.embed_manager import EmbeddingManager

gencom_app = typer.Typer(help="Commands for generating agent comments on content.")
logger = logging.getLogger(__name__)

@gencom_app.command("message")
def gencom_message(
    message_id: str = typer.Argument(..., help="ID of the message to generate comment for"),
    prompt_template: Optional[str] = typer.Option(
        None, "--prompt-template", help="Prompt template (use {content} as placeholder)."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="If set and no prompt template is provided, prompt for one interactively."
    ),
    override: bool = typer.Option(
        False, "--override", help="Force reprocessing even if an output already exists."
    ),
    provider: str = typer.Option(
        "ollama", "--provider", help="Content agent provider to use (e.g., 'ollama', 'openai')."
    ),
    generate_embedding: bool = typer.Option(
        False, "--embed", help="Generate embeddings for the created gencom content."
    ),
    embedding_provider: Optional[str] = typer.Option(
        None, "--embed-provider", help="Provider to use for embeddings (defaults to gencom provider)."
    ),
    max_words: Optional[int] = typer.Option(
        None, "--max-words", help="Maximum word count for the generated comment."
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum token count for the generated comment."
    ),
    preview_prompt: bool = typer.Option(
        True, "--preview-prompt/--no-preview-prompt", help="Show prompt preview and confirm before proceeding."
    )
):
    """
    Generate an AI comment for a specific message.

    The generated comment is stored as an AgentOutput with output_type 'gencom'.
    If --embed is specified, the comment will also have embeddings generated.
    """
    if not prompt_template and interactive:
        prompt_template = typer.prompt("Enter the prompt template (use {content} as placeholder)")
    elif not prompt_template:
        prompt_template = "Please provide a comment on the following content:\n\n{content}"
    
    # Create effective prompt with length constraints
    effective_prompt = prompt_template
    if max_words:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
    if max_tokens:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
    
    # Show prompt template preview and get confirmation if enabled
    if preview_prompt:
        typer.echo(f"\nPrompt template that will be used:\n---\n{effective_prompt}\n---")
        if typer.confirm("Do you want to proceed with this prompt?", default=True):
            manager = ContentTaskManager(provider=provider)
        else:
            if typer.confirm("Would you like to edit the prompt?", default=True):
                prompt_template = typer.prompt("Enter the updated prompt template")
                # Show the updated prompt with any length constraints
                effective_prompt = prompt_template
                if max_words:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
                if max_tokens:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
                typer.echo(f"\nUpdated prompt template:\n---\n{effective_prompt}\n---")
                if typer.confirm("Do you want to proceed with this prompt?", default=True):
                    manager = ContentTaskManager(provider=provider)
                else:
                    typer.echo("Operation cancelled.")
                    raise typer.Exit(code=0)
            else:
                typer.echo("Operation cancelled.")
                raise typer.Exit(code=0)
    else:
        # Skip preview and proceed directly
        manager = ContentTaskManager(provider=provider)
    
    try:
        # Validate that the message exists
        with get_session() as session:
            msg = session.query(Message).filter_by(id=message_id).first()
            if not msg:
                typer.echo(f"Error: Message with ID {message_id} not found.")
                raise typer.Exit(code=1)
        
        output = manager.run_task_for_target(
            target_type="message",
            target_id=message_id,
            task="gencom",
            prompt_template=prompt_template,
            override=override,
            max_words=max_words,
            max_tokens=max_tokens
        )
        
        typer.echo(f"Generated comment for message {message_id} (AgentOutput ID: {output.id}).")
        
        # Generate embedding if requested
        if generate_embedding:
            embed_provider = embedding_provider or provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
            
            # Generate embedding for the gencom content
            embedding = embedding_manager.embed_texts(
                texts=[output.content],
                parent_ids=[str(output.id)],
                parent_type="agent_output"
            )
            
            typer.echo(f"Generated embedding for the comment (Embedding ID: {embedding[0].id}).")
            
    except Exception as e:
        typer.echo(f"Error processing message: {e}")
        raise typer.Exit(code=1)

@gencom_app.command("conversation")
def gencom_conversation(
    conversation_id: str = typer.Argument(..., help="ID of the conversation to generate comment for"),
    prompt_template: Optional[str] = typer.Option(
        None, "--prompt-template", help="Prompt template (use {content} as placeholder)."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="If set and no prompt template is provided, prompt for one interactively."
    ),
    override: bool = typer.Option(
        False, "--override", help="Force reprocessing even if an output already exists."
    ),
    provider: str = typer.Option(
        "ollama", "--provider", help="Content agent provider to use (e.g., 'ollama', 'openai')."
    ),
    generate_embedding: bool = typer.Option(
        False, "--embed", help="Generate embeddings for the created gencom content."
    ),
    embedding_provider: Optional[str] = typer.Option(
        None, "--embed-provider", help="Provider to use for embeddings (defaults to gencom provider)."
    ),
    max_words: Optional[int] = typer.Option(
        None, "--max-words", help="Maximum word count for the generated comment."
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum token count for the generated comment."
    ),
    preview_prompt: bool = typer.Option(
        True, "--preview-prompt/--no-preview-prompt", help="Show prompt preview and confirm before proceeding."
    )
):
    """
    Generate an AI comment for an entire conversation.

    The generated comment is stored as an AgentOutput with output_type 'gencom'.
    If --embed is specified, the comment will also have embeddings generated.
    """
    if not prompt_template and interactive:
        prompt_template = typer.prompt("Enter the prompt template (use {content} as placeholder)")
    elif not prompt_template:
        prompt_template = "Please provide a comment on the following conversation transcript:\n\n{content}"
    
    # Create effective prompt with length constraints
    effective_prompt = prompt_template
    if max_words:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
    if max_tokens:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
    
    # Show prompt template preview and get confirmation if enabled
    if preview_prompt:
        typer.echo(f"\nPrompt template that will be used:\n---\n{effective_prompt}\n---")
        if typer.confirm("Do you want to proceed with this prompt?", default=True):
            manager = ContentTaskManager(provider=provider)
        else:
            if typer.confirm("Would you like to edit the prompt?", default=True):
                prompt_template = typer.prompt("Enter the updated prompt template")
                # Show the updated prompt with any length constraints
                effective_prompt = prompt_template
                if max_words:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
                if max_tokens:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
                typer.echo(f"\nUpdated prompt template:\n---\n{effective_prompt}\n---")
                if typer.confirm("Do you want to proceed with this prompt?", default=True):
                    manager = ContentTaskManager(provider=provider)
                else:
                    typer.echo("Operation cancelled.")
                    raise typer.Exit(code=0)
            else:
                typer.echo("Operation cancelled.")
                raise typer.Exit(code=0)
    else:
        # Skip preview and proceed directly
        manager = ContentTaskManager(provider=provider)
    
    try:
        # Validate that the conversation exists
        with get_session() as session:
            conv = session.query(Conversation).filter_by(id=conversation_id).first()
            if not conv:
                typer.echo(f"Error: Conversation with ID {conversation_id} not found.")
                raise typer.Exit(code=1)
        
        output = manager.run_task_for_target(
            target_type="conversation",
            target_id=conversation_id,
            task="gencom",
            prompt_template=prompt_template,
            override=override,
            max_words=max_words,
            max_tokens=max_tokens
        )
        
        typer.echo(f"Generated comment for conversation {conversation_id} (AgentOutput ID: {output.id}).")
        
        # Generate embedding if requested
        if generate_embedding:
            embed_provider = embedding_provider or provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
            
            # Generate embedding for the gencom content
            embedding = embedding_manager.embed_texts(
                texts=[output.content],
                parent_ids=[str(output.id)],
                parent_type="agent_output"
            )
            
            typer.echo(f"Generated embedding for the comment (Embedding ID: {embedding[0].id}).")
            
    except Exception as e:
        typer.echo(f"Error processing conversation: {e}")
        raise typer.Exit(code=1)

@gencom_app.command("chunk")
def gencom_chunk(
    chunk_id: str = typer.Argument(..., help="ID of the chunk to generate comment for"),
    prompt_template: Optional[str] = typer.Option(
        None, "--prompt-template", help="Prompt template (use {content} as placeholder)."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="If set and no prompt template is provided, prompt for one interactively."
    ),
    override: bool = typer.Option(
        False, "--override", help="Force reprocessing even if an output already exists."
    ),
    provider: str = typer.Option(
        "ollama", "--provider", help="Content agent provider to use (e.g., 'ollama', 'openai')."
    ),
    generate_embedding: bool = typer.Option(
        False, "--embed", help="Generate embeddings for the created gencom content."
    ),
    embedding_provider: Optional[str] = typer.Option(
        None, "--embed-provider", help="Provider to use for embeddings (defaults to gencom provider)."
    ),
    max_words: Optional[int] = typer.Option(
        None, "--max-words", help="Maximum word count for the generated comment."
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum token count for the generated comment."
    ),
    preview_prompt: bool = typer.Option(
        True, "--preview-prompt/--no-preview-prompt", help="Show prompt preview and confirm before proceeding."
    )
):
    """
    Generate an AI comment for a specific content chunk.

    The generated comment is stored as an AgentOutput with output_type 'gencom'.
    If --embed is specified, the comment will also have embeddings generated.
    """
    if not prompt_template and interactive:
        prompt_template = typer.prompt("Enter the prompt template (use {content} as placeholder)")
    elif not prompt_template:
        prompt_template = "Please provide a comment on the following content chunk:\n\n{content}"
    
    # Create effective prompt with length constraints
    effective_prompt = prompt_template
    if max_words:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
    if max_tokens:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
    
    # Show prompt template preview and get confirmation if enabled
    if preview_prompt:
        typer.echo(f"\nPrompt template that will be used:\n---\n{effective_prompt}\n---")
        if typer.confirm("Do you want to proceed with this prompt?", default=True):
            manager = ContentTaskManager(provider=provider)
        else:
            if typer.confirm("Would you like to edit the prompt?", default=True):
                prompt_template = typer.prompt("Enter the updated prompt template")
                # Show the updated prompt with any length constraints
                effective_prompt = prompt_template
                if max_words:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
                if max_tokens:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
                typer.echo(f"\nUpdated prompt template:\n---\n{effective_prompt}\n---")
                if typer.confirm("Do you want to proceed with this prompt?", default=True):
                    manager = ContentTaskManager(provider=provider)
                else:
                    typer.echo("Operation cancelled.")
                    raise typer.Exit(code=0)
            else:
                typer.echo("Operation cancelled.")
                raise typer.Exit(code=0)
    else:
        # Skip preview and proceed directly
        manager = ContentTaskManager(provider=provider)
    
    try:
        # Validate that the chunk exists
        with get_session() as session:
            chunk = session.query(Chunk).filter_by(id=chunk_id).first()
            if not chunk:
                typer.echo(f"Error: Chunk with ID {chunk_id} not found.")
                raise typer.Exit(code=1)
        
        output = manager.run_task_for_target(
            target_type="chunk",
            target_id=chunk_id,
            task="gencom",
            prompt_template=prompt_template,
            override=override,
            max_words=max_words,
            max_tokens=max_tokens
        )
        
        typer.echo(f"Generated comment for chunk {chunk_id} (AgentOutput ID: {output.id}).")
        
        # Generate embedding if requested
        if generate_embedding:
            embed_provider = embedding_provider or provider
            embedding_manager = EmbeddingManager(provider=embed_provider)
            
            # Generate embedding for the gencom content
            embedding = embedding_manager.embed_texts(
                texts=[output.content],
                parent_ids=[str(output.id)],
                parent_type="agent_output"
            )
            
            typer.echo(f"Generated embedding for the comment (Embedding ID: {embedding[0].id}).")
            
    except Exception as e:
        typer.echo(f"Error processing chunk: {e}")
        raise typer.Exit(code=1)

@gencom_app.command("all")
def gencom_all(
    min_word_count: int = typer.Option(
        5, "--min-word-count", help="Minimum words a message must have."
    ),
    target_type: str = typer.Option(
        "message", "--target-type", help="Target type to process ('message', 'conversation')."
    ),
    roles: Optional[List[str]] = typer.Option(
        ["user"], "--role", help="Only process messages with this role (can be specified multiple times)."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Optional limit on the number of items to process."
    ),
    days: Optional[int] = typer.Option(
        None, "--days", help="Only process items from the last N days."
    ),
    prompt_template: Optional[str] = typer.Option(
        None, "--prompt-template", help="Prompt template (use {content} as placeholder)."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="If set and no prompt template is provided, prompt for one interactively."
    ),
    override: bool = typer.Option(
        False, "--override", help="Force reprocessing even if an output already exists."
    ),
    provider: str = typer.Option(
        "ollama", "--provider", help="Content agent provider to use (e.g., 'ollama', 'openai')."
    ),
    generate_embedding: bool = typer.Option(
        False, "--embed", help="Generate embeddings for each generated comment."
    ),
    embedding_provider: Optional[str] = typer.Option(
        None, "--embed-provider", help="Provider to use for embeddings (defaults to gencom provider)."
    ),
    max_words: Optional[int] = typer.Option(
        None, "--max-words", help="Maximum word count for the generated comments."
    ),
    max_tokens: Optional[int] = typer.Option(
        None, "--max-tokens", help="Maximum token count for the generated comments."
    ),
    preview_prompt: bool = typer.Option(
        True, "--preview-prompt/--no-preview-prompt", help="Show prompt preview and confirm before proceeding."
    )
):
    """
    Generate AI comments on content items that meet the criteria.

    The generated comments are stored as AgentOutput objects with output_type 'gencom'.
    By default, only messages with role 'user' and with at least the specified word count 
    are processed.

    If --embed is specified, embeddings will be generated for each comment created.
    """
    if not prompt_template and interactive:
        prompt_template = typer.prompt("Enter the prompt template (use {content} as placeholder)")
    elif not prompt_template:
        if target_type == "message":
            prompt_template = "Please provide a comment on the following content:\n\n{content}"
        elif target_type == "conversation":
            prompt_template = "Please provide a comment on the following conversation transcript:\n\n{content}"
        elif target_type == "chunk":
            prompt_template = "Please provide a comment on the following content chunk:\n\n{content}"
    
    # Create effective prompt with length constraints
    effective_prompt = prompt_template
    if max_words:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
    if max_tokens:
        effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
    
    # Show prompt template preview and get confirmation if enabled
    if preview_prompt:
        typer.echo(f"\nPrompt template that will be used:\n---\n{effective_prompt}\n---")
        if typer.confirm("Do you want to proceed with this prompt?", default=True):
            logger.info(f"Starting generated comment process for {target_type}s.")
            manager = ContentTaskManager(provider=provider)
        else:
            if typer.confirm("Would you like to edit the prompt?", default=True):
                prompt_template = typer.prompt("Enter the updated prompt template")
                # Show the updated prompt with any length constraints
                effective_prompt = prompt_template
                if max_words:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_words} words."
                if max_tokens:
                    effective_prompt = f"{effective_prompt}\n\nPlease limit your response to approximately {max_tokens} tokens."
                typer.echo(f"\nUpdated prompt template:\n---\n{effective_prompt}\n---")
                if typer.confirm("Do you want to proceed with this prompt?", default=True):
                    logger.info(f"Starting generated comment process for {target_type}s.")
                    manager = ContentTaskManager(provider=provider)
                else:
                    typer.echo("Operation cancelled.")
                    raise typer.Exit(code=0)
            else:
                typer.echo("Operation cancelled.")
                raise typer.Exit(code=0)
    else:
        # Skip preview and proceed directly
        logger.info(f"Starting generated comment process for {target_type}s.")
        manager = ContentTaskManager(provider=provider)
    
    # Initialize an embedding manager if needed
    embedding_manager = None
    if generate_embedding:
        embed_provider = embedding_provider or provider
        embedding_manager = EmbeddingManager(provider=embed_provider)

    with get_session() as session:
        items_to_process = []
        
        if target_type == "message":
            # Build base query: messages with non-null content and at least the min word count
            word_count_expr = func.array_length(func.regexp_split_to_array(Message.content, r'\s+'), 1)
            base_query = session.query(Message).filter(Message.content.isnot(None))
            base_query = base_query.filter(word_count_expr >= min_word_count)
            
            # Apply role filter as IN operator for multiple roles
            if roles:
                base_query = base_query.filter(Message.role.in_([r.lower() for r in roles]))
            
            # Apply date filter if specified
            if days:
                date_filter = text(f"created_at > NOW() - INTERVAL '{days} days'")
                base_query = base_query.filter(date_filter)
                
            # Apply limit if specified
            if limit:
                base_query = base_query.limit(limit)
                
            items_to_process = base_query.all()
            
        elif target_type == "conversation":
            # Build base query for conversations
            base_query = session.query(Conversation)
            
            # Apply date filter if specified
            if days:
                date_filter = text(f"created_at > NOW() - INTERVAL '{days} days'")
                base_query = base_query.filter(date_filter)
                
            # Apply limit if specified
            if limit:
                base_query = base_query.limit(limit)
                
            items_to_process = base_query.all()
            
        elif target_type == "chunk":
            # Build base query for chunks
            word_count_expr = func.array_length(func.regexp_split_to_array(Chunk.content, r'\s+'), 1)
            base_query = session.query(Chunk).filter(Chunk.content.isnot(None))
            base_query = base_query.filter(word_count_expr >= min_word_count)
            
            # Apply date filter if specified
            if days:
                date_filter = text(f"created_at > NOW() - INTERVAL '{days} days'")
                base_query = base_query.filter(date_filter)
                
            # Apply limit if specified
            if limit:
                base_query = base_query.limit(limit)
                
            items_to_process = base_query.all()
        
        else:
            typer.echo(f"Error: Unsupported target type '{target_type}'.")
            raise typer.Exit(code=1)

    total = len(items_to_process)
    logger.info(f"Found {total} {target_type}s to process.")

    processed = 0
    failed = 0
    skipped = 0
    embedding_success = 0
    embedding_failed = 0
    
    for item in items_to_process:
        try:
            # Check if an output already exists for this item
            with get_session() as session:
                existing = session.query(AgentOutput).filter(
                    AgentOutput.target_type == target_type,
                    AgentOutput.target_id == item.id,
                    AgentOutput.output_type == "gencom"
                ).first()
                
                if existing and not override:
                    logger.info(f"{target_type.capitalize()} {item.id} already has a gencom output, skipping.")
                    skipped += 1
                    continue
            
            output = manager.run_task_for_target(
                target_type=target_type,
                target_id=str(item.id),
                task="gencom",
                prompt_template=prompt_template,
                override=override,
                max_words=max_words,
                max_tokens=max_tokens
            )
            
            logger.info(f"{target_type.capitalize()} {item.id} processed (AgentOutput ID: {output.id}).")
            processed += 1
            
            # Generate embedding if requested
            if generate_embedding and embedding_manager:
                try:
                    embedding = embedding_manager.embed_texts(
                        texts=[output.content],
                        parent_ids=[str(output.id)],
                        parent_type="agent_output"
                    )
                    logger.info(f"Generated embedding for comment (Embedding ID: {embedding[0].id}).")
                    embedding_success += 1
                except Exception as embed_err:
                    logger.error(f"Error generating embedding for output {output.id}: {embed_err}")
                    embedding_failed += 1
                    
        except Exception as e:
            logger.error(f"Error processing {target_type} {item.id}: {e}")
            failed += 1

    result_msg = f"Generated comments complete.\n"
    result_msg += f"Processed: {processed}, Failed: {failed}, Skipped: {skipped}"
    if generate_embedding:
        result_msg += f"\nEmbeddings: {embedding_success} created, {embedding_failed} failed"
    typer.echo(result_msg)

if __name__ == "__main__":
    gencom_app()
