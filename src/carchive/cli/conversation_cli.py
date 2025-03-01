"""
CLI commands for conversation-related operations.
"""

import logging
import typer
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from uuid import UUID

from carchive.conversation_service import ConversationService
from carchive.core.conversation_service import list_conversations as core_list_conversations
from carchive.core.conversation_service import get_conversation, get_conversation_with_messages, export_conversation
from carchive.schemas.db_objects import ConversationRead, MessageRead

app = typer.Typer(name="conversation", help="Commands for managing conversations")
conversation_app = typer.Typer(name="conversation", help="Legacy conversation commands")
logger = logging.getLogger(__name__)

# Add the same commands to the legacy conversation_app
@conversation_app.command("list")
def list_conversations_legacy_cmd(
    limit: int = typer.Option(50, help="Maximum number of conversations to return"),
    offset: int = typer.Option(0, help="Number of conversations to skip"),
    sort_order: str = typer.Option("desc", help="Sort order: asc or desc"),
    sort_by: str = typer.Option("created_at", help="Field to sort by: created_at, title, original_create_time, original_update_time"),
    filter_text: Optional[str] = typer.Option(None, "--search", help="Filter by title text"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider (e.g., 'chatgpt', 'claude')"),
    use_original_dates: bool = typer.Option(True, help="Use original dates from meta_info when available")
):
    """
    List conversations with optional filtering and sorting.
    """
    # Just call the original implementation - but only pass the parameters it accepts
    list_conversations_cmd(
        limit=limit,
        offset=offset,
        sort_order=sort_order,
        sort_by=sort_by,
        filter_text=filter_text,
        provider=provider
    )

@conversation_app.command("get")
def get_conversation_legacy_cmd(
    conversation_id: str = typer.Argument(..., help="ID of the conversation to retrieve"),
    with_messages: bool = typer.Option(False, help="Include messages in the output")
):
    """
    Get details of a specific conversation.
    """
    # Just call the original implementation
    get_conversation_cmd(conversation_id=conversation_id, with_messages=with_messages)

@conversation_app.command("export")
def export_conversation_legacy_cmd(
    conversation_id: str = typer.Argument(..., help="ID of the conversation to export"),
    output_path: str = typer.Argument(..., help="Path to save the exported JSON file")
):
    """
    Export a conversation to a JSON file.
    """
    # Just call the original implementation
    export_conversation_cmd(conversation_id=conversation_id, output_path=output_path)

@app.command("ingest")
def ingest_conversations(
    file_path: str = typer.Argument(..., help="Path to JSON or ZIP file containing conversations"),
    skip_existing: bool = typer.Option(True, help="Skip conversations that already exist in the database"),
    extract_media: bool = typer.Option(True, help="Extract and create references to media files"),
    verbose: bool = typer.Option(False, help="Enable verbose logging")
):
    """
    Ingest conversations from a JSON or ZIP file with enhanced timestamp and media handling.
    """
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: File {file_path} does not exist.")
        raise typer.Exit(code=1)
    
    typer.echo(f"Ingesting conversations from {file_path}...")
    conversations_ingested, messages_ingested = ConversationService.ingest_file(
        file_path=path,
        skip_existing=skip_existing,
        extract_media=extract_media,
        verbose=verbose
    )
    
    typer.echo(f"Successfully ingested {conversations_ingested} conversations with {messages_ingested} messages.")

@app.command("analyze-media")
def analyze_media_references(
    file_path: str = typer.Argument(..., help="Path to JSON file containing conversations"),
    output_path: Optional[str] = typer.Option(None, help="Path to save extracted references as JSON")
):
    """
    Analyze and extract media references from conversations without ingesting into the database.
    """
    path = Path(file_path)
    if not path.exists():
        typer.echo(f"Error: File {file_path} does not exist.")
        raise typer.Exit(code=1)
    
    output = None
    if output_path:
        output = Path(output_path)
    
    typer.echo(f"Analyzing media references in {file_path}...")
    media_references = ConversationService.extract_media_references_only(
        file_path=path,
        output_path=output
    )
    
    # Compile statistics on media
    total_refs = len(media_references)
    existing_files = sum(1 for ref in media_references if ref.get('exists', False))
    missing_files = total_refs - existing_files
    
    # Count by media type
    media_types = {}
    for ref in media_references:
        media_type = ref.get('media_type', 'unknown')
        media_types[media_type] = media_types.get(media_type, 0) + 1
    
    # Count by source
    sources = {}
    for ref in media_references:
        source = ref.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1
    
    # Print report
    typer.echo("\n=== Media References Analysis ===")
    typer.echo(f"Total references: {total_refs}")
    typer.echo(f"Files found: {existing_files} ({100*existing_files/total_refs:.1f}%)")
    typer.echo(f"Files missing: {missing_files} ({100*missing_files/total_refs:.1f}%)")
    
    typer.echo("\nBy media type:")
    for media_type, count in sorted(media_types.items(), key=lambda x: x[1], reverse=True):
        typer.echo(f"  {media_type}: {count} ({100*count/total_refs:.1f}%)")
    
    typer.echo("\nBy reference source:")
    for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
        typer.echo(f"  {source}: {count} ({100*count/total_refs:.1f}%)")
    
    if output_path:
        typer.echo(f"\nDetailed references saved to {output_path}")
    else:
        typer.echo("\nUse --output-path to save detailed references to a file.")

@app.command("fix-timestamps")
def fix_timestamps_cmd(
    json_path: str = typer.Argument(..., help="Path to the original conversations.json file"),
    dry_run: bool = typer.Option(False, help="Perform a dry run without making changes")
):
    """
    Fix missing timestamps in conversation meta_info from original conversations.json file.
    """
    from carchive.database.models import Conversation
    from carchive.database.session import get_session
    import json
    
    try:
        # Load conversations from JSON
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            conversations = data
            if isinstance(data, dict) and "conversations" in data:
                conversations = data["conversations"]
        
        typer.echo(f"Loaded {len(conversations)} conversations from JSON")
        
        # Create a mapping of titles to timestamps 
        title_map = {}
        for convo in conversations:
            title = convo.get('title')
            create_time = convo.get('create_time')
            update_time = convo.get('update_time')
            
            if title and (create_time or update_time):
                title_map[title] = (create_time, update_time)
                
                # Debug the first few conversations
                if len(title_map) <= 3:
                    typer.echo(f"Debug - JSON conversation: title='{title}', create_time={create_time}, update_time={update_time}")
        
        typer.echo(f"Found timestamps for {len(title_map)} conversations in JSON")
        
        # Update database entries
        with get_session() as session:
            # Get all conversations, we'll filter with Python
            query = session.query(Conversation)
            
            total_convos = query.count()
            fixed_count = 0
            
            for convo in query:
                # For debugging specific conversation
                if dry_run and convo.id.hex[:8] == "51783db7":  # Debug for our test example
                    typer.echo(f"Debug - Convo ID: {convo.id}, Title: {convo.title}")
                    typer.echo(f"Debug - Found in title_map: {convo.title in title_map}")
                    
                # Search by title
                if convo.title and convo.title in title_map:
                    create_time, update_time = title_map[convo.title]
                    
                    # Check if timestamps are missing
                    needs_update = False
                    
                    # Need to convert meta_info to dict if it's not already
                    meta_info = convo.meta_info
                    if not isinstance(meta_info, dict):
                        try:
                            meta_info = dict(meta_info)
                        except (TypeError, ValueError):
                            # If conversion fails, start with existing keys
                            meta_info = {}
                            if convo.meta_info:
                                meta_info['source_conversation_id'] = convo.meta_info.get('source_conversation_id')
                                meta_info['is_anonymous'] = convo.meta_info.get('is_anonymous')
                    
                    if create_time and ('create_time' not in meta_info or not meta_info.get('create_time')):
                        meta_info['create_time'] = create_time
                        needs_update = True
                    
                    if update_time and ('update_time' not in meta_info or not meta_info.get('update_time')):
                        meta_info['update_time'] = update_time
                        needs_update = True
                        
                    if needs_update:
                        convo.meta_info = meta_info
                        if not dry_run:
                            # Save the changes
                            session.add(convo)
                            fixed_count += 1
                        else:
                            typer.echo(f"Would fix timestamps for '{convo.title}': create_time={create_time}, update_time={update_time}")
                            fixed_count += 1
            
            if not dry_run and fixed_count > 0:
                session.commit()
            
            typer.echo(f"Checked {total_convos} conversations, fixed {fixed_count} timestamp issues")
            if dry_run and fixed_count > 0:
                typer.echo("This was a dry run. Run without --dry-run to apply changes.")
    
    except Exception as e:
        typer.echo(f"Error fixing timestamps: {e}")
        raise typer.Exit(code=1)

@app.command("list")
def list_conversations_cmd(
    limit: int = typer.Option(50, help="Maximum number of conversations to return"),
    offset: int = typer.Option(0, help="Number of conversations to skip"),
    sort_order: str = typer.Option("desc", help="Sort order: asc or desc"),
    sort_by: str = typer.Option("created_at", help="Field to sort by: created_at, title"),
    filter_text: Optional[str] = typer.Option(None, "--search", help="Filter by title text"),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider (e.g., 'chatgpt', 'claude')")
):
    """
    List conversations with optional filtering and sorting.
    """
    from carchive.database.models import Conversation, Provider
    from carchive.database.session import get_session
    from sqlalchemy import desc, asc, func
    
    try:
        # Validate sort order
        if sort_order.lower() not in ["asc", "desc"]:
            typer.echo("Error: sort_order must be 'asc' or 'desc'")
            raise typer.Exit(code=1)
        
        # Validate sort_by
        valid_sort_fields = ["created_at", "title"]
        if sort_by not in valid_sort_fields:
            typer.echo(f"Error: sort_by must be one of {', '.join(valid_sort_fields)}")
            raise typer.Exit(code=1)
        
        with get_session() as session:
            # Build the query
            query = session.query(Conversation)
            
            # Apply title filter
            if filter_text:
                query = query.filter(Conversation.title.ilike(f"%{filter_text}%"))
            
            # Apply provider filter
            if provider:
                # Convert provider name to provider_id
                provider_query = session.query(Provider.id).filter(
                    Provider.name.ilike(f"{provider}")
                ).first()
                
                if not provider_query:
                    typer.echo(f"Error: Provider '{provider}' not found. Available providers:")
                    # List available providers
                    providers = session.query(Provider.name).all()
                    for p in providers:
                        typer.echo(f"  - {p[0]}")
                    raise typer.Exit(code=1)
                
                provider_id = provider_query[0]
                query = query.filter(Conversation.provider_id == provider_id)
            
            # Get total count before pagination
            total_count = query.count()
            
            # Apply sorting
            if sort_by == "title":
                if sort_order.lower() == "asc":
                    query = query.order_by(asc(Conversation.title))
                else:
                    query = query.order_by(desc(Conversation.title))
            else:  # Default to created_at
                if sort_order.lower() == "asc":
                    query = query.order_by(asc(Conversation.created_at))
                else:
                    query = query.order_by(desc(Conversation.created_at))
            
            # Apply pagination
            conversations = query.offset(offset).limit(limit).all()
            
            # Display results
            typer.echo(f"Found {total_count} conversations (showing {len(conversations)})")
            
            for conversation in conversations:
                # Format the date (using database timestamp as fallback)
                create_time = conversation.created_at.strftime("%Y-%m-%d %H:%M")
                
                # Get title (fallback to ID if no title)
                title = conversation.title or "[Untitled]"
                
                # Check if meta_info has original timestamps
                original_time = None
                if conversation.meta_info and conversation.meta_info.get('create_time'):
                    try:
                        timestamp = float(conversation.meta_info['create_time'])
                        original_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
                        create_time = original_time  # Use original time if available
                    except (ValueError, TypeError):
                        pass
                
                # Get provider name
                provider_name = "[Unknown]"
                if conversation.provider_id:
                    provider_result = session.query(Provider.name).filter(
                        Provider.id == conversation.provider_id
                    ).first()
                    if provider_result:
                        provider_name = provider_result[0]
                
                typer.echo(f"- {conversation.id}: [{create_time}] [{provider_name}] {title}")
    
    except Exception as e:
        typer.echo(f"Error listing conversations: {e}")
        raise typer.Exit(code=1)

@app.command("get")
def get_conversation_cmd(
    conversation_id: str = typer.Argument(..., help="ID of the conversation to retrieve"),
    with_messages: bool = typer.Option(False, help="Include messages in the output")
):
    """
    Get details of a specific conversation.
    """
    from carchive.database.models import Conversation, Message, Provider
    from carchive.database.session import get_session
    
    try:
        # Convert string ID to UUID
        try:
            from uuid import UUID
            conversation_id = UUID(conversation_id)
        except ValueError:
            typer.echo(f"Invalid conversation ID format: {conversation_id}")
            raise typer.Exit(code=1)
        
        with get_session() as session:
            # Fetch the conversation
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            
            if not conversation:
                typer.echo(f"Conversation {conversation_id} not found")
                raise typer.Exit(code=1)
            
            # Display conversation details
            typer.echo(f"Conversation: {conversation.id}")
            typer.echo(f"Title: {conversation.title or '[Untitled]'}")
            
            # Get provider information
            provider_name = "[Unknown]"
            if conversation.provider_id:
                provider_result = session.query(Provider.name, Provider.description).filter(
                    Provider.id == conversation.provider_id
                ).first()
                if provider_result:
                    provider_name = provider_result[0]
                    provider_description = provider_result[1] or ""
                    typer.echo(f"Provider: {provider_name} {provider_description}")
                else:
                    typer.echo(f"Provider: {conversation.provider_id} (ID only)")
            else:
                typer.echo("Provider: [Unknown]")
            
            # Handle timestamps
            create_time = conversation.created_at.strftime("%Y-%m-%d %H:%M:%S")
            update_time = conversation.created_at.strftime("%Y-%m-%d %H:%M:%S")  # Default to create time
            
            # Check for original timestamps in meta_info
            if conversation.meta_info:
                if conversation.meta_info.get('create_time'):
                    try:
                        timestamp = float(conversation.meta_info['create_time'])
                        create_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pass
                
                if conversation.meta_info.get('update_time'):
                    try:
                        timestamp = float(conversation.meta_info['update_time'])
                        update_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pass
            
            typer.echo(f"Created: {create_time}")
            typer.echo(f"Updated: {update_time}")
            
            # Display model info if available
            if conversation.model_info:
                model_name = conversation.model_info.get('name', '[Unknown]')
                model_version = conversation.model_info.get('version', '')
                if model_version:
                    typer.echo(f"Model: {model_name} (v{model_version})")
                else:
                    typer.echo(f"Model: {model_name}")
            
            if with_messages:
                # Fetch messages for the conversation
                messages = session.query(Message).filter(
                    Message.conversation_id == conversation_id
                ).order_by(Message.created_at).all()
                
                typer.echo(f"Messages: {len(messages)}")
                
                # Display message summaries
                if messages:
                    typer.echo("\nMessages:")
                    for i, message in enumerate(messages):
                        created = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Determine role from meta_info
                        role = "unknown"
                        if message.meta_info and "author_role" in message.meta_info:
                            role = message.meta_info["author_role"]
                        elif message.role:  # Use database role field if available
                            role = message.role
                        
                        # Prepare content preview
                        content = message.content or ""
                        content_preview = (content[:60] + "...") if len(content) > 60 else content
                        
                        typer.echo(f"{i+1}. [{created}] {role}: {content_preview}")
    
    except Exception as e:
        typer.echo(f"Error retrieving conversation: {e}")
        raise typer.Exit(code=1)

@app.command("providers")
def list_providers_cmd():
    """
    List all available providers in the database.
    """
    from carchive.database.models import Provider
    from carchive.database.session import get_session
    
    try:
        with get_session() as session:
            providers = session.query(Provider).order_by(Provider.name).all()
            
            typer.echo(f"Found {len(providers)} providers:")
            for provider in providers:
                description = f" - {provider.description}" if provider.description else ""
                typer.echo(f"- {provider.name}{description} (ID: {provider.id})")
                
    except Exception as e:
        typer.echo(f"Error listing providers: {e}")
        raise typer.Exit(code=1)
        
@app.command("stats")
def provider_stats_cmd():
    """
    Show statistics about conversations by provider.
    """
    from carchive.database.models import Conversation, Provider, Message
    from carchive.database.session import get_session
    from sqlalchemy import func, desc
    
    try:
        with get_session() as session:
            # Get count of conversations by provider
            provider_stats = session.query(
                Provider.name, 
                Provider.description,
                func.count(Conversation.id).label('conversation_count')
            ).outerjoin(
                Conversation, 
                Conversation.provider_id == Provider.id
            ).group_by(
                Provider.id, 
                Provider.name, 
                Provider.description
            ).order_by(
                desc('conversation_count')
            ).all()
            
            # Get message counts per provider
            message_counts = {}
            for provider_name, _, _ in provider_stats:
                provider = session.query(Provider).filter(Provider.name == provider_name).first()
                if provider:
                    message_count = session.query(func.count(Message.id)).join(
                        Conversation, 
                        Conversation.id == Message.conversation_id
                    ).filter(
                        Conversation.provider_id == provider.id
                    ).scalar() or 0
                    
                    message_counts[provider_name] = message_count
            
            # Get total counts
            total_conversations = session.query(func.count(Conversation.id)).scalar() or 0
            total_messages = session.query(func.count(Message.id)).scalar() or 0
            
            # Display results
            typer.echo("Conversation Statistics by Provider\n")
            typer.echo(f"Total Conversations: {total_conversations}")
            typer.echo(f"Total Messages: {total_messages}\n")
            
            typer.echo("Provider Breakdown:")
            for provider_name, provider_description, conversation_count in provider_stats:
                message_count = message_counts.get(provider_name, 0)
                conv_percent = (conversation_count / total_conversations * 100) if total_conversations > 0 else 0
                msg_percent = (message_count / total_messages * 100) if total_messages > 0 else 0
                
                description = f" - {provider_description}" if provider_description else ""
                typer.echo(f"- {provider_name}{description}")
                typer.echo(f"  Conversations: {conversation_count} ({conv_percent:.1f}%)")
                typer.echo(f"  Messages: {message_count} ({msg_percent:.1f}%)")
                if conversation_count > 0:
                    typer.echo(f"  Avg. Messages/Conversation: {message_count/conversation_count:.1f}")
                typer.echo("")
                
    except Exception as e:
        typer.echo(f"Error getting provider statistics: {e}")
        raise typer.Exit(code=1)

@app.command("export")
def export_conversation_cmd(
    conversation_id: str = typer.Argument(..., help="ID of the conversation to export"),
    output_path: str = typer.Argument(..., help="Path to save the exported JSON file")
):
    """
    Export a conversation to a JSON file.
    """
    from carchive.database.models import Conversation, Message, Provider
    from carchive.database.session import get_session
    import json
    
    try:
        # Convert string ID to UUID
        try:
            from uuid import UUID
            conversation_id = UUID(conversation_id)
        except ValueError:
            typer.echo(f"Invalid conversation ID format: {conversation_id}")
            raise typer.Exit(code=1)
        
        with get_session() as session:
            # Fetch the conversation
            conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
            
            if not conversation:
                typer.echo(f"Conversation {conversation_id} not found")
                raise typer.Exit(code=1)
            
            # Fetch messages for the conversation
            messages = session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at).all()
            
            # Get provider info
            provider_name = None
            if conversation.provider_id:
                provider = session.query(Provider).filter(Provider.id == conversation.provider_id).first()
                if provider:
                    provider_name = provider.name
            
            # Create the export structure
            export_data = {
                "id": str(conversation.id),
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat(),
                "provider": provider_name,
                "provider_id": str(conversation.provider_id) if conversation.provider_id else None,
                "model_info": conversation.model_info,
                "meta_info": conversation.meta_info,
                "messages": []
            }
            
            # Add messages
            for message in messages:
                export_data["messages"].append({
                    "id": str(message.id),
                    "content": message.content,
                    "role": message.role,
                    "created_at": message.created_at.isoformat(),
                    "meta_info": message.meta_info
                })
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            typer.echo(f"Conversation {conversation_id} exported to {output_path}")
            
    except Exception as e:
        typer.echo(f"Error exporting conversation: {e}")
        raise typer.Exit(code=1)