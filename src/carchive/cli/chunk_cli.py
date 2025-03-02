"""
CLI commands for managing message chunks.

This module provides commands for creating, viewing, and manipulating
chunks extracted from messages and other text content.
"""

import uuid
import json
from typing import List, Optional, Dict, Any
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from carchive.chunk.chunker import ChunkType
from carchive.chunk.manager import ChunkManager
from carchive.database.session import get_session
from carchive.database.models import Message, Conversation, Chunk

chunk_app = typer.Typer(help="Commands to manage message chunks.")
console = Console()


@chunk_app.command("create")
def create_chunks_cmd(
    message_id: str = typer.Argument(..., help="ID of the message to chunk"),
    chunk_type: str = typer.Option(
        "paragraph", "--type", "-t",
        help="Chunking strategy (paragraph, sentence, token, fixed_length, custom)"
    ),
    output_buffer: Optional[str] = typer.Option(
        None, "--buffer", "-b",
        help="Name of buffer to store chunks in"
    ),
    chunk_size: Optional[int] = typer.Option(
        None, "--size", "-s",
        help="Size of chunks (for fixed_length strategy)"
    ),
    chunk_overlap: Optional[int] = typer.Option(
        None, "--overlap", "-o",
        help="Overlap between chunks (for fixed_length strategy)"
    ),
    separator: Optional[str] = typer.Option(
        None, "--separator",
        help="Separator for custom chunking"
    ),
    keep_separator: bool = typer.Option(
        False, "--keep-separator/--remove-separator",
        help="Whether to keep separators in custom chunks"
    ),
    show_chunks: bool = typer.Option(
        True, "--show/--no-show",
        help="Display created chunks after creation"
    )
):
    """
    Create chunks from a message using the specified strategy.
    """
    try:
        # Convert message_id to UUID
        message_id_uuid = uuid.UUID(message_id)
        
        # Prepare options
        options = {}
        if chunk_size is not None:
            options["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            options["chunk_overlap"] = chunk_overlap
        if separator is not None:
            options["separator"] = separator
        if keep_separator is not None:
            options["keep_separator"] = keep_separator
        
        # Create chunks
        result = ChunkManager.create_chunks_from_message(
            message_id_uuid,
            chunk_type,
            options,
            output_buffer
        )
        
        # Show results
        console.print(f"Created {result.count} chunks using '{chunk_type}' strategy.")
        
        if output_buffer:
            console.print(f"Chunks added to buffer: {output_buffer}")
        
        if show_chunks and result.count > 0:
            # Show chunk table
            table = Table(title=f"Message Chunks ({chunk_type})")
            table.add_column("Position", style="cyan")
            table.add_column("Chunk ID", style="green")
            table.add_column("Content", style="yellow")
            table.add_column("Chars", style="magenta")
            
            for chunk in result.chunks:
                # Truncate content for display
                content = chunk.content
                if len(content) > 80:
                    content = content[:77] + "..."
                
                table.add_row(
                    str(chunk.position),
                    str(chunk.id),
                    content,
                    f"{len(chunk.content)}"
                )
            
            console.print(table)
            
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("create-from-conversation")
def create_chunks_from_conversation_cmd(
    conversation_id: str = typer.Argument(..., help="ID of the conversation"),
    chunk_type: str = typer.Option(
        "paragraph", "--type", "-t",
        help="Chunking strategy (paragraph, sentence, token, fixed_length, custom)"
    ),
    output_buffer: Optional[str] = typer.Option(
        None, "--buffer", "-b",
        help="Name of buffer to store chunks in"
    ),
    message_types: Optional[List[str]] = typer.Option(
        None, "--role", "-r",
        help="Message roles to include (e.g., 'user', 'assistant')"
    ),
    max_messages: Optional[int] = typer.Option(
        None, "--max", "-m",
        help="Maximum number of messages to process"
    ),
    chunk_size: Optional[int] = typer.Option(
        None, "--size", "-s",
        help="Size of chunks (for fixed_length strategy)"
    ),
    chunk_overlap: Optional[int] = typer.Option(
        None, "--overlap", "-o",
        help="Overlap between chunks (for fixed_length strategy)"
    ),
    separator: Optional[str] = typer.Option(
        None, "--separator",
        help="Separator for custom chunking"
    )
):
    """
    Create chunks from all messages in a conversation.
    """
    try:
        # Convert conversation_id to UUID
        conversation_id_uuid = uuid.UUID(conversation_id)
        
        # Prepare options
        options = {}
        if chunk_size is not None:
            options["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            options["chunk_overlap"] = chunk_overlap
        if separator is not None:
            options["separator"] = separator
        
        # Create chunks
        result = ChunkManager.create_chunks_from_conversation(
            conversation_id_uuid,
            message_types,
            chunk_type,
            options,
            output_buffer,
            max_messages
        )
        
        # Show results
        console.print(f"Processed {result['total_messages']} messages:")
        console.print(f"  - Success: {result['success_count']} messages")
        console.print(f"  - Failure: {result['failure_count']} messages")
        console.print(f"  - Total chunks created: {result['total_chunks']}")
        
        if output_buffer:
            console.print(f"Chunks added to buffer: {output_buffer}")
        
        if result['failures']:
            console.print("\nMessages with errors:", style="bold red")
            for failure in result['failures'][:5]:  # Show first 5 failures
                console.print(f"  - {failure['message_id']}: {failure['error']}")
            
            if len(result['failures']) > 5:
                console.print(f"  ... and {len(result['failures']) - 5} more errors")
        
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("list")
def list_chunks_cmd(
    message_id: Optional[str] = typer.Option(
        None, "--message", "-m",
        help="Show chunks for specific message"
    ),
    conversation_id: Optional[str] = typer.Option(
        None, "--conversation", "-c",
        help="Show chunks for all messages in a conversation"
    ),
    chunk_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="Filter by chunk type"
    ),
    limit: int = typer.Option(
        20, "--limit", "-n",
        help="Maximum number of chunks to display"
    ),
    content_length: int = typer.Option(
        80, "--content-length", "-l",
        help="Maximum length of content to display"
    )
):
    """
    List chunks for a message or conversation.
    """
    if not message_id and not conversation_id:
        console.print("Error: Either message ID or conversation ID must be specified", style="bold red")
        raise typer.Exit(code=1)
    
    try:
        with get_session() as session:
            chunks = []
            title = "Chunks"
            
            if message_id:
                # Show chunks for a specific message
                message_id_uuid = uuid.UUID(message_id)
                query = session.query(Chunk).filter(Chunk.message_id == message_id_uuid)
                
                # Get message for title
                message = session.query(Message).filter(Message.id == message_id_uuid).first()
                if message:
                    message_preview = message.content[:50] + "..." if message.content and len(message.content) > 50 else message.content
                    title = f"Chunks for Message {message_id} (Role: {message.role})"
                else:
                    title = f"Chunks for Message {message_id}"
                
            elif conversation_id:
                # Show chunks for all messages in a conversation
                conversation_id_uuid = uuid.UUID(conversation_id)
                
                # Get message IDs in this conversation
                message_ids = [mid[0] for mid in session.query(Message.id).filter(
                    Message.conversation_id == conversation_id_uuid
                ).all()]
                
                query = session.query(Chunk).filter(Chunk.message_id.in_(message_ids))
                
                # Get conversation for title
                conversation = session.query(Conversation).filter(Conversation.id == conversation_id_uuid).first()
                if conversation:
                    title = f"Chunks for Conversation: {conversation.title or conversation_id}"
                else:
                    title = f"Chunks for Conversation {conversation_id}"
            
            # Apply chunk type filter if specified
            if chunk_type:
                query = query.filter(Chunk.chunk_type == chunk_type)
                title += f" (Type: {chunk_type})"
            
            # Order and limit
            chunks = query.order_by(Chunk.message_id, Chunk.position).limit(limit).all()
            
            # Display chunks
            if not chunks:
                console.print("No chunks found.")
                return
            
            table = Table(title=title)
            table.add_column("ID", style="cyan")
            table.add_column("Type", style="blue")
            table.add_column("Position", style="magenta")
            table.add_column("Content", style="yellow")
            table.add_column("Length", style="green")
            
            for chunk in chunks:
                # Truncate content for display
                content = chunk.content
                if len(content) > content_length:
                    content = content[:content_length - 3] + "..."
                
                table.add_row(
                    str(chunk.id),
                    chunk.chunk_type,
                    str(chunk.position),
                    content,
                    str(len(chunk.content))
                )
            
            console.print(table)
            
            if len(chunks) == limit:
                console.print(f"Note: Only showing first {limit} chunks. Use --limit option to see more.")
            
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("show")
def show_chunk_cmd(
    chunk_id: str = typer.Argument(..., help="ID of the chunk to show"),
    full_content: bool = typer.Option(
        True, "--full-content/--summary",
        help="Display full content or just a summary"
    ),
    syntax_highlight: bool = typer.Option(
        True, "--syntax-highlight/--plain",
        help="Apply syntax highlighting to content"
    )
):
    """
    Show details of a specific chunk.
    """
    try:
        # Convert chunk_id to UUID
        chunk_id_uuid = uuid.UUID(chunk_id)
        
        # Get chunk
        chunk = ChunkManager.get_chunk_by_id(chunk_id_uuid)
        
        if not chunk:
            console.print(f"Chunk {chunk_id} not found.", style="bold red")
            raise typer.Exit(code=1)
        
        # Display chunk details
        console.print(f"[bold cyan]Chunk ID:[/] {chunk.id}")
        console.print(f"[bold cyan]Message ID:[/] {chunk.message_id}")
        console.print(f"[bold cyan]Type:[/] {chunk.chunk_type}")
        console.print(f"[bold cyan]Position:[/] {chunk.position}")
        console.print(f"[bold cyan]Start/End:[/] {chunk.start_char or 'N/A'} - {chunk.end_char or 'N/A'}")
        console.print(f"[bold cyan]Length:[/] {len(chunk.content)} characters")
        console.print(f"[bold cyan]Created:[/] {chunk.created_at}")
        
        if chunk.meta_info:
            console.print("\n[bold cyan]Metadata:[/]")
            for key, value in chunk.meta_info.items():
                console.print(f"  [cyan]{key}:[/] {value}")
        
        # Display content
        console.print("\n[bold cyan]Content:[/]")
        
        if not full_content and len(chunk.content) > 200:
            # Show summary
            preview = chunk.content[:197] + "..."
            console.print(Panel(preview, title="Content Preview"))
            console.print(f"Note: Showing first 200 of {len(chunk.content)} characters. Use --full-content to see all.")
        else:
            # Show full content with optional syntax highlighting
            if syntax_highlight:
                # Simple language detection based on chunk content
                language = "text"
                if chunk.content.startswith("```"):
                    # Extract language from code block if possible
                    first_line = chunk.content.split("\n")[0]
                    if len(first_line) > 3:
                        language = first_line[3:].strip()
                    content = "\n".join(chunk.content.split("\n")[1:])
                else:
                    content = chunk.content
                
                syntax = Syntax(content, language, theme="monokai", line_numbers=True)
                console.print(syntax)
            else:
                console.print(Panel(chunk.content, title="Content"))
        
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("delete")
def delete_chunks_cmd(
    message_id: Optional[str] = typer.Option(
        None, "--message", "-m",
        help="Delete chunks for specific message"
    ),
    conversation_id: Optional[str] = typer.Option(
        None, "--conversation", "-c",
        help="Delete chunks for all messages in a conversation"
    ),
    chunk_id: Optional[str] = typer.Option(
        None, "--chunk", "-k",
        help="Delete a specific chunk"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Skip confirmation prompt"
    )
):
    """
    Delete chunks by message, conversation, or chunk ID.
    """
    if not message_id and not conversation_id and not chunk_id:
        console.print("Error: Either message ID, conversation ID, or chunk ID must be specified", style="bold red")
        raise typer.Exit(code=1)
    
    try:
        # Determine what to delete
        delete_type = "chunk"
        delete_id = chunk_id
        target_desc = f"chunk {chunk_id}"
        
        if message_id:
            delete_type = "message"
            delete_id = message_id
            target_desc = f"all chunks for message {message_id}"
        elif conversation_id:
            delete_type = "conversation"
            delete_id = conversation_id
            target_desc = f"all chunks for conversation {conversation_id}"
        
        # Confirm deletion
        if not force:
            confirm = typer.confirm(f"Are you sure you want to delete {target_desc}?")
            if not confirm:
                console.print("Deletion cancelled.")
                return
        
        # Perform deletion
        if delete_type == "chunk":
            # Delete a specific chunk
            with get_session() as session:
                chunk = session.query(Chunk).filter(Chunk.id == uuid.UUID(delete_id)).first()
                if not chunk:
                    console.print(f"Chunk {delete_id} not found.", style="bold red")
                    raise typer.Exit(code=1)
                
                session.delete(chunk)
                session.commit()
                console.print(f"Deleted chunk {delete_id}.")
        
        elif delete_type == "message":
            # Delete all chunks for a message
            count = ChunkManager.delete_chunks_by_message(uuid.UUID(delete_id))
            console.print(f"Deleted {count} chunks for message {delete_id}.")
        
        elif delete_type == "conversation":
            # Delete all chunks for a conversation
            count = ChunkManager.delete_chunks_by_conversation(uuid.UUID(delete_id))
            console.print(f"Deleted {count} chunks for conversation {delete_id}.")
        
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("search")
def search_chunks_cmd(
    query: str = typer.Argument(..., help="Search query"),
    message_id: Optional[str] = typer.Option(
        None, "--message", "-m",
        help="Search within a specific message"
    ),
    conversation_id: Optional[str] = typer.Option(
        None, "--conversation", "-c",
        help="Search within a conversation"
    ),
    chunk_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="Filter by chunk type"
    ),
    exact: bool = typer.Option(
        False, "--exact/--fuzzy",
        help="Perform exact match instead of substring match"
    ),
    limit: int = typer.Option(
        10, "--limit", "-n",
        help="Maximum number of results to return"
    ),
    output_buffer: Optional[str] = typer.Option(
        None, "--buffer", "-b",
        help="Name of buffer to store search results in"
    ),
    content_length: int = typer.Option(
        80, "--content-length", "-l",
        help="Maximum length of content to display"
    )
):
    """
    Search for chunks containing specific text.
    """
    try:
        # Convert IDs to UUIDs if provided
        message_id_uuid = uuid.UUID(message_id) if message_id else None
        conversation_id_uuid = uuid.UUID(conversation_id) if conversation_id else None
        
        # Perform search
        chunks = ChunkManager.search_chunks(
            query,
            exact=exact,
            limit=limit,
            chunk_type=chunk_type,
            message_id=message_id_uuid,
            conversation_id=conversation_id_uuid
        )
        
        # Display results
        if not chunks:
            console.print("No matching chunks found.")
            return
        
        # Create a title based on search criteria
        title_parts = [f"Search Results for '{query}'"]
        if exact:
            title_parts[0] += " (exact match)"
        if message_id:
            title_parts.append(f"in Message {message_id}")
        if conversation_id:
            title_parts.append(f"in Conversation {conversation_id}")
        if chunk_type:
            title_parts.append(f"of Type {chunk_type}")
        
        title = " ".join(title_parts)
        
        table = Table(title=title)
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Message", style="magenta", no_wrap=True)
        table.add_column("Content", style="yellow")
        
        for chunk in chunks:
            # Truncate content for display
            content = chunk.content
            if len(content) > content_length:
                content = content[:content_length - 3] + "..."
            
            # Highlight search terms if not exact match
            if not exact:
                try:
                    content = content.replace(query, f"[bold]{query}[/bold]")
                except:
                    pass
            
            # Format message ID
            message_id_short = str(chunk.message_id)
            if len(message_id_short) > 8:
                message_id_short = message_id_short[:8] + "..."
            
            table.add_row(
                str(chunk.id),
                chunk.chunk_type,
                message_id_short,
                content
            )
        
        console.print(table)
        
        # Add results to buffer if requested
        if output_buffer and chunks:
            chunk_ids = [chunk.id for chunk in chunks]
            added = ChunkManager.add_chunks_to_buffer(chunk_ids, output_buffer)
            console.print(f"Added {added} chunks to buffer '{output_buffer}'.")
        
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("stats")
def chunk_stats_cmd():
    """
    Show statistics about chunks in the database.
    """
    try:
        # Get chunk statistics
        stats = ChunkManager.get_chunk_stats()
        
        console.print("[bold]Chunk Statistics[/bold]")
        console.print(f"Total chunks: {stats['total_chunks']}")
        console.print(f"Recent chunks (last 7 days): {stats['recent_chunks']}")
        console.print(f"Messages with chunks: {stats['messages_with_chunks']}")
        console.print(f"Average chunk length: {stats['avg_chunk_length']:.2f} characters")
        
        console.print("\n[bold]Chunks by type:[/bold]")
        for chunk_type, count in stats['chunks_by_type'].items():
            console.print(f"  {chunk_type}: {count}")
        
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)


@chunk_app.command("rechunk")
def rechunk_message_cmd(
    message_id: str = typer.Argument(..., help="ID of the message to rechunk"),
    chunk_type: str = typer.Option(
        "paragraph", "--type", "-t",
        help="Chunking strategy (paragraph, sentence, token, fixed_length, custom)"
    ),
    output_buffer: Optional[str] = typer.Option(
        None, "--buffer", "-b",
        help="Name of buffer to store chunks in"
    ),
    chunk_size: Optional[int] = typer.Option(
        None, "--size", "-s",
        help="Size of chunks (for fixed_length strategy)"
    ),
    chunk_overlap: Optional[int] = typer.Option(
        None, "--overlap", "-o",
        help="Overlap between chunks (for fixed_length strategy)"
    ),
    separator: Optional[str] = typer.Option(
        None, "--separator",
        help="Separator for custom chunking"
    ),
    keep_separator: bool = typer.Option(
        False, "--keep-separator/--remove-separator",
        help="Whether to keep separators in custom chunks"
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Skip confirmation prompt"
    )
):
    """
    Delete existing chunks for a message and create new ones.
    """
    try:
        # Convert message_id to UUID
        message_id_uuid = uuid.UUID(message_id)
        
        # Check if message has existing chunks
        with get_session() as session:
            existing_count = session.query(Chunk).filter(Chunk.message_id == message_id_uuid).count()
        
        if existing_count > 0 and not force:
            confirm = typer.confirm(f"Message has {existing_count} existing chunks. Delete and recreate?")
            if not confirm:
                console.print("Rechunking cancelled.")
                return
        
        # Prepare options
        options = {}
        if chunk_size is not None:
            options["chunk_size"] = chunk_size
        if chunk_overlap is not None:
            options["chunk_overlap"] = chunk_overlap
        if separator is not None:
            options["separator"] = separator
        if keep_separator is not None:
            options["keep_separator"] = keep_separator
        
        # Rechunk message
        result = ChunkManager.rechunk_message(
            message_id_uuid,
            chunk_type,
            options,
            output_buffer
        )
        
        # Show results
        if existing_count > 0:
            console.print(f"Deleted {existing_count} existing chunks.")
        
        console.print(f"Created {result.count} new chunks using '{chunk_type}' strategy.")
        
        if output_buffer:
            console.print(f"Chunks added to buffer: {output_buffer}")
        
    except ValueError as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"Error: {str(e)}", style="bold red")
        raise typer.Exit(code=1)