"""
CLI commands for managing results buffers.

This module provides commands for creating, viewing, and manipulating
buffers that store search results and other collections of entities.
"""

import uuid
import json
import typer
from typing import List, Optional, Dict, Any, Union
from rich.console import Console
from rich.table import Table
from datetime import datetime

from carchive.buffer.buffer_manager import BufferManager
from carchive.buffer.schemas import (
    BufferCreateSchema, BufferUpdateSchema, BufferFilterCriteria,
    BufferType, BufferItemSchema, BufferOperationType
)
from carchive.buffer.operations import (
    filter_by_role, filter_by_content, filter_by_days, filter_by_has_image,
    buffer_intersection, buffer_union, buffer_difference
)

buffer_app = typer.Typer(help="Commands to manage search result buffers.")
console = Console()


@buffer_app.command("create")
def create_buffer_cmd(
    name: str = typer.Argument(..., help="Name for the new buffer"),
    buffer_type: str = typer.Option(
        "session", "--type", "-t", 
        help="Buffer type (ephemeral, session, persistent)"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d",
        help="Optional description for the buffer"
    )
):
    """
    Create a new empty buffer with the given name.
    """
    try:
        # Convert string buffer type to enum
        buffer_type_enum = BufferType(buffer_type)
        
        # Create buffer data
        buffer_data = BufferCreateSchema(
            name=name,
            buffer_type=buffer_type_enum,
            description=description
        )
        
        # Create buffer
        buffer = BufferManager.create_buffer(buffer_data)
        
        typer.echo(f"Created buffer {buffer.id}: {buffer.name} ({buffer.buffer_type})")
        return buffer.id
    except ValueError as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("list")
def list_buffers_cmd(
    type_filter: Optional[str] = typer.Option(
        None, "--type", "-t", 
        help="Filter by buffer type (ephemeral, session, persistent)"
    ),
    session_only: bool = typer.Option(
        True, "--session-only/--all",
        help="Show only buffers in the current session (default) or all buffers"
    )
):
    """
    List all buffers, optionally filtered by type.
    """
    try:
        # Generate session ID for filtering
        session_id = None
        if session_only:
            session_id = BufferManager._generate_session_id()
        
        # Get buffers
        buffers = BufferManager.list_buffers(
            session_id=session_id,
            buffer_type=type_filter
        )
        
        if not buffers:
            typer.echo("No buffers found.")
            return
        
        # Create a table
        table = Table(title="Results Buffers")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Items", style="magenta")
        table.add_column("Created", style="yellow")
        table.add_column("Description")
        
        # Add rows to the table
        from carchive.database.session import get_session
        
        with get_session() as session:
            for buffer in buffers:
                # Count items - use a query instead of accessing items directly
                from carchive.database.models import BufferItem
                items_count = session.query(BufferItem).filter(BufferItem.buffer_id == buffer.id).count()
                
                # Format created timestamp
                created = buffer.created_at.strftime("%Y-%m-%d %H:%M:%S") if buffer.created_at else "Unknown"
                
                table.add_row(
                    str(buffer.id),
                    buffer.name,
                    buffer.buffer_type,
                    str(items_count),
                    created,
                    buffer.description or ""
                )
        
        # Print the table
        console.print(table)
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("show")
def show_buffer_cmd(
    buffer_name: str = typer.Argument(..., help="Name of the buffer to show"),
    limit: int = typer.Option(
        10, "--limit", "-n",
        help="Maximum number of items to show"
    ),
    offset: int = typer.Option(
        0, "--offset", "-o",
        help="Offset for pagination"
    ),
    content_length: int = typer.Option(
        100, "--content-length", "-l",
        help="Maximum length of content to display"
    )
):
    """
    Show the contents of a buffer with the given name.
    """
    try:
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer
        buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
        if not buffer:
            typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
            return
        
        # Get detailed buffer with contents
        buffer_detail = BufferManager.get_buffer_with_contents(buffer.id)
        if not buffer_detail:
            typer.echo(f"Error retrieving buffer contents.")
            return
        
        # Create a table for buffer metadata
        meta_table = Table(title=f"Buffer: {buffer_name}")
        meta_table.add_column("ID", style="cyan")
        meta_table.add_column("Type", style="blue")
        meta_table.add_column("Items", style="magenta")
        meta_table.add_column("Created", style="yellow")
        
        # Add buffer metadata
        meta_table.add_row(
            str(buffer_detail.id),
            buffer_detail.buffer_type,
            str(buffer_detail.item_count),
            buffer_detail.created_at.strftime("%Y-%m-%d %H:%M:%S") if buffer_detail.created_at else "Unknown"
        )
        
        console.print(meta_table)
        
        if buffer_detail.description:
            console.print(f"Description: {buffer_detail.description}")
        
        # Show buffer contents
        if not buffer_detail.items:
            console.print("Buffer is empty.")
            return
        
        # Apply pagination
        paginated_items = buffer_detail.items[offset:offset+limit]
        
        # Create a table for buffer contents
        content_table = Table(title=f"Contents (showing {len(paginated_items)} of {buffer_detail.item_count} items)")
        content_table.add_column("Type", style="blue")
        content_table.add_column("ID", style="cyan")
        content_table.add_column("Content", style="green")
        content_table.add_column("Created", style="yellow")
        
        # Add rows for buffer items
        for item in paginated_items:
            item_type = type(item).__name__.replace("Read", "")
            
            # Extract content based on item type
            content = ""
            if hasattr(item, 'content'):
                content = item.content
            elif hasattr(item, 'title'):
                content = item.title
                
            # Truncate content if needed
            if content and len(content) > content_length:
                content = content[:content_length] + "..."
                
            # Format created timestamp
            created = ""
            if hasattr(item, 'created_at'):
                created = item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else ""
                
            content_table.add_row(
                item_type,
                str(item.id),
                content,
                created
            )
            
        console.print(content_table)
        
        # Show pagination info if needed
        if buffer_detail.item_count > limit:
            total_pages = (buffer_detail.item_count + limit - 1) // limit
            current_page = (offset // limit) + 1
            console.print(f"Page {current_page} of {total_pages}")
            console.print(f"Use --offset {offset + limit} to see the next page")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("clear")
def clear_buffer_cmd(
    buffer_name: str = typer.Argument(..., help="Name of the buffer to clear")
):
    """
    Remove all items from a buffer without deleting the buffer itself.
    """
    try:
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer
        buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
        if not buffer:
            typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
            return
        
        # Clear buffer
        success = BufferManager.clear_buffer(buffer.id)
        if success:
            typer.echo(f"Buffer '{buffer_name}' has been cleared.")
        else:
            typer.echo(f"Failed to clear buffer '{buffer_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("delete")
def delete_buffer_cmd(
    buffer_name: str = typer.Argument(..., help="Name of the buffer to delete")
):
    """
    Delete a buffer and all its items.
    """
    try:
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer
        buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
        if not buffer:
            typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
            return
        
        # Delete buffer
        success = BufferManager.delete_buffer(buffer.id)
        if success:
            typer.echo(f"Buffer '{buffer_name}' has been deleted.")
        else:
            typer.echo(f"Failed to delete buffer '{buffer_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("filter")
def filter_buffer_cmd(
    buffer_name: str = typer.Argument(..., help="Name of the source buffer"),
    target_name: Optional[str] = typer.Option(
        None, "--target", "-t",
        help="Name for the target buffer (creates a new buffer if not specified)"
    ),
    role: Optional[str] = typer.Option(
        None, "--role", "-r",
        help="Filter by message role (e.g., 'user', 'assistant')"
    ),
    content: Optional[str] = typer.Option(
        None, "--content", "-c",
        help="Filter by text content"
    ),
    days: Optional[int] = typer.Option(
        None, "--days", "-d",
        help="Filter by maximum age in days"
    ),
    has_image: Optional[bool] = typer.Option(
        None, "--has-image/--no-image",
        help="Filter by presence of images"
    )
):
    """
    Filter a buffer's contents by various criteria.
    """
    try:
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get source buffer
        source_buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
        if not source_buffer:
            typer.echo(f"Source buffer '{buffer_name}' not found in the current session.")
            return
        
        # Get target buffer if specified
        target_buffer_id = None
        if target_name:
            target_buffer = BufferManager.get_buffer_by_name(target_name, session_id)
            if target_buffer:
                target_buffer_id = target_buffer.id
            else:
                # Create a new target buffer
                target_data = BufferCreateSchema(
                    name=target_name,
                    buffer_type=BufferType(source_buffer.buffer_type),
                    description=f"Filtered from {buffer_name}"
                )
                target_buffer = BufferManager.create_buffer(target_data)
                target_buffer_id = target_buffer.id
                typer.echo(f"Created target buffer '{target_name}'.")
        
        # Create filter criteria
        filter_criteria = BufferFilterCriteria(
            role=role,
            content=content,
            days=days,
            has_image=has_image
        )
        
        # Apply filter
        result = BufferManager.filter_buffer(source_buffer.id, filter_criteria, target_buffer_id)
        
        if isinstance(result, uuid.UUID):
            # New buffer was created
            typer.echo(f"Created new buffer with ID {result} containing filtered results.")
        else:
            # Items were added to target buffer
            typer.echo(f"Added {result} items to target buffer '{target_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("to-collection")
def buffer_to_collection_cmd(
    buffer_name: str = typer.Argument(..., help="Name of the buffer to convert"),
    collection_name: str = typer.Argument(..., help="Name for the new collection"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d",
        help="Optional description for the collection"
    )
):
    """
    Convert a buffer to a collection.
    """
    try:
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer
        buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
        if not buffer:
            typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
            return
        
        # Convert to collection
        collection_id = BufferManager.convert_buffer_to_collection(
            buffer.id, collection_name, description
        )
        
        typer.echo(f"Created collection '{collection_name}' with ID {collection_id} from buffer '{buffer_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("intersect")
def buffer_intersect_cmd(
    buffers: List[str] = typer.Argument(..., help="Names of buffers to intersect"),
    target_name: Optional[str] = typer.Option(
        None, "--target", "-t",
        help="Name for the target buffer (creates a new buffer if not specified)"
    )
):
    """
    Create a buffer with items that appear in all specified buffers.
    """
    try:
        if len(buffers) < 2:
            typer.echo("At least two buffers are required for intersection.")
            raise typer.Exit(code=1)
        
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer IDs
        buffer_ids = []
        for buffer_name in buffers:
            buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
            if not buffer:
                typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
                return
            buffer_ids.append(buffer.id)
        
        # Get target buffer if specified
        target_buffer_id = None
        if target_name:
            target_buffer = BufferManager.get_buffer_by_name(target_name, session_id)
            if target_buffer:
                target_buffer_id = target_buffer.id
            else:
                # Create a new target buffer
                target_data = BufferCreateSchema(
                    name=target_name,
                    buffer_type=BufferType.SESSION,
                    description=f"Intersection of {len(buffers)} buffers"
                )
                target_buffer = BufferManager.create_buffer(target_data)
                target_buffer_id = target_buffer.id
                typer.echo(f"Created target buffer '{target_name}'.")
        
        # Apply intersection
        result = buffer_intersection(
            buffer_ids,
            target_buffer_id,
            name=target_name or f"Intersection_{'+'.join(buffers)}"
        )
        
        if isinstance(result, uuid.UUID):
            # New buffer was created
            typer.echo(f"Created new buffer with ID {result} containing intersection results.")
        else:
            # Items were added to target buffer
            typer.echo(f"Added {result} items to target buffer '{target_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("union")
def buffer_union_cmd(
    buffers: List[str] = typer.Argument(..., help="Names of buffers to combine"),
    target_name: Optional[str] = typer.Option(
        None, "--target", "-t",
        help="Name for the target buffer (creates a new buffer if not specified)"
    ),
    deduplicate: bool = typer.Option(
        True, "--deduplicate/--allow-duplicates",
        help="Remove duplicate items (default) or allow duplicates"
    )
):
    """
    Create a buffer with unique items from all specified buffers.
    """
    try:
        if len(buffers) < 2:
            typer.echo("At least two buffers are required for union.")
            raise typer.Exit(code=1)
        
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get buffer IDs
        buffer_ids = []
        for buffer_name in buffers:
            buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
            if not buffer:
                typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
                return
            buffer_ids.append(buffer.id)
        
        # Get target buffer if specified
        target_buffer_id = None
        if target_name:
            target_buffer = BufferManager.get_buffer_by_name(target_name, session_id)
            if target_buffer:
                target_buffer_id = target_buffer.id
            else:
                # Create a new target buffer
                target_data = BufferCreateSchema(
                    name=target_name,
                    buffer_type=BufferType.SESSION,
                    description=f"Union of {len(buffers)} buffers"
                )
                target_buffer = BufferManager.create_buffer(target_data)
                target_buffer_id = target_buffer.id
                typer.echo(f"Created target buffer '{target_name}'.")
        
        # Apply union
        result = buffer_union(
            buffer_ids,
            target_buffer_id,
            name=target_name or f"Union_{'+'.join(buffers)}",
            deduplicate=deduplicate
        )
        
        if isinstance(result, uuid.UUID):
            # New buffer was created
            typer.echo(f"Created new buffer with ID {result} containing union results.")
        else:
            # Items were added to target buffer
            typer.echo(f"Added {result} items to target buffer '{target_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)


@buffer_app.command("difference")
def buffer_difference_cmd(
    primary_buffer: str = typer.Argument(..., help="Name of the primary buffer"),
    exclude_buffers: List[str] = typer.Argument(..., help="Names of buffers to exclude"),
    target_name: Optional[str] = typer.Option(
        None, "--target", "-t",
        help="Name for the target buffer (creates a new buffer if not specified)"
    )
):
    """
    Create a buffer with items that appear in the primary buffer but not in any exclude buffers.
    """
    try:
        if not exclude_buffers:
            typer.echo("At least one exclude buffer is required for difference.")
            raise typer.Exit(code=1)
        
        # Generate session ID for filtering
        session_id = BufferManager._generate_session_id()
        
        # Get primary buffer
        primary = BufferManager.get_buffer_by_name(primary_buffer, session_id)
        if not primary:
            typer.echo(f"Primary buffer '{primary_buffer}' not found in the current session.")
            return
        
        # Get exclude buffer IDs
        exclude_ids = []
        for buffer_name in exclude_buffers:
            buffer = BufferManager.get_buffer_by_name(buffer_name, session_id)
            if not buffer:
                typer.echo(f"Buffer '{buffer_name}' not found in the current session.")
                return
            exclude_ids.append(buffer.id)
        
        # Get target buffer if specified
        target_buffer_id = None
        if target_name:
            target_buffer = BufferManager.get_buffer_by_name(target_name, session_id)
            if target_buffer:
                target_buffer_id = target_buffer.id
            else:
                # Create a new target buffer
                target_data = BufferCreateSchema(
                    name=target_name,
                    buffer_type=BufferType.SESSION,
                    description=f"Difference: {primary_buffer} minus {len(exclude_buffers)} buffers"
                )
                target_buffer = BufferManager.create_buffer(target_data)
                target_buffer_id = target_buffer.id
                typer.echo(f"Created target buffer '{target_name}'.")
        
        # Apply difference
        result = buffer_difference(
            primary.id,
            exclude_ids,
            target_buffer_id,
            name=target_name or f"Diff_{primary_buffer}_minus_{len(exclude_buffers)}"
        )
        
        if isinstance(result, uuid.UUID):
            # New buffer was created
            typer.echo(f"Created new buffer with ID {result} containing difference results.")
        else:
            # Items were added to target buffer
            typer.echo(f"Added {result} items to target buffer '{target_name}'.")
    except Exception as e:
        typer.echo(f"Error: {str(e)}")
        raise typer.Exit(code=1)