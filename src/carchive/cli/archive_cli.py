"""Command-line interface for accessing and verifying archive exports directly."""

import os
import sys
import json
import tempfile
import logging
from typing import Optional, List
from pathlib import Path
from datetime import datetime

import typer
import rich
from rich.table import Table
from rich.console import Console

# Suppress NumExpr messages
logging.getLogger('numexpr').setLevel(logging.WARNING)
logging.getLogger('numexpr.utils').setLevel(logging.WARNING)

from carchive.archive import ArchiveAccessor
from carchive.database.models import Conversation, Message, Media
from carchive.database.session import get_session

app = typer.Typer(help="Tools for directly working with archive export files")
console = Console()

@app.command("info")
def archive_info(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
):
    """Display basic information about an archive file."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        stats = accessor.get_archive_stats()
        
        console.print(f"[bold]Archive:[/bold] {archive_path}")
        console.print(f"[bold]Size:[/bold] {stats['archive_size'] // 1024 // 1024} MB")
        console.print(f"[bold]Conversations:[/bold] {stats['conversations']}")
        console.print(f"[bold]Messages:[/bold] {stats['messages']}")
        console.print(f"[bold]Media files:[/bold] {stats['media_files']}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

@app.command("list")
def list_conversations(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of conversations to show"),
):
    """List conversations in the archive file."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        conversations = accessor.get_conversations()
        
        table = Table(title=f"Conversations in {archive_path.name}")
        table.add_column("ID", style="cyan")
        table.add_column("Title")
        table.add_column("Created", style="green")
        table.add_column("Messages", style="magenta")
        table.add_column("Model", style="yellow")
        
        for i, conv in enumerate(conversations[:limit]):
            summary = accessor.get_conversation_summary(conv)
            created = datetime.fromtimestamp(summary['create_time']).strftime('%Y-%m-%d') if summary['create_time'] else "Unknown"
            
            table.add_row(
                summary['id'],
                summary['title'],
                created,
                str(summary['message_count']),
                summary['model']
            )
        
        console.print(table)
        
        if len(conversations) > limit:
            console.print(f"\nShowing {limit} of {len(conversations)} conversations. Use --limit to show more.")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

@app.command("view")
def view_conversation(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
    conversation_id: str = typer.Argument(..., help="ID of the conversation to view"),
    metadata_only: bool = typer.Option(False, "--meta", "-m", help="Only show metadata for the conversation"),
    verify_media: bool = typer.Option(False, "--verify-media", help="Verify media files exist in the archive"),
    verify_database: bool = typer.Option(False, "--verify-db", help="Verify content against database entries"),
):
    """View a specific conversation from the archive."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        conversation = accessor.get_conversation_by_id(conversation_id)
        
        if not conversation:
            console.print(f"[bold red]Error:[/bold red] Conversation with ID '{conversation_id}' not found")
            sys.exit(1)
        
        # Get conversation summary with error handling
        try:
            summary = accessor.get_conversation_summary(conversation)
        except Exception as e:
            console.print(f"[bold red]Error retrieving conversation summary:[/bold red] {str(e)}")
            console.print("[yellow]Displaying partial information[/yellow]")
            # Create minimal summary with fallbacks
            summary = {
                'id': conversation.get('conversation_id', 'Unknown'),
                'title': conversation.get('title', 'Untitled'),
                'create_time': conversation.get('create_time'),
                'update_time': conversation.get('update_time'),
                'model': conversation.get('default_model_slug', 'Unknown'),
                'message_count': len(conversation.get('mapping', {}))
            }
        
        # Display conversation details with error handling
        try:
            console.print(f"[bold]Conversation:[/bold] {summary.get('title', 'Untitled')}")
            console.print(f"[bold]ID:[/bold] {summary.get('id', 'Unknown')}")
            
            # Safely display timestamps
            create_time = summary.get('create_time')
            if create_time and isinstance(create_time, (int, float)):
                console.print(f"[bold]Created:[/bold] {datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                console.print("[bold]Created:[/bold] Unknown")
                
            update_time = summary.get('update_time')
            if update_time and isinstance(update_time, (int, float)):
                console.print(f"[bold]Updated:[/bold] {datetime.fromtimestamp(update_time).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                console.print("[bold]Updated:[/bold] Unknown")
                
            console.print(f"[bold]Model:[/bold] {summary.get('model', 'Unknown')}")
            console.print(f"[bold]Messages:[/bold] {summary.get('message_count', 0)}")
        except Exception as e:
            console.print(f"[bold red]Error displaying conversation details:[/bold red] {str(e)}")
        
        if not metadata_only:
            # Get messages
            messages = accessor.get_messages(conversation)
            
            console.print("\n[bold]Messages:[/bold]")
            for msg in messages:
                try:
                    depth = msg['depth']
                    message = msg['data'] if 'data' in msg else {}
                    
                    # Handle missing or malformed message data
                    if not message:
                        console.print(f"  [dim]Message {msg.get('id', 'unknown')} has no content data[/dim]")
                        continue
                    
                    # Get message components with safe fallbacks
                    role = message.get('author', {}).get('role', 'unknown')
                    content_obj = message.get('content', {}) or {}  # Handle None case
                    content_type = content_obj.get('content_type', 'text')
                    parts = content_obj.get('parts', []) if content_obj else []
                    
                    # Format content with error checking
                    try:
                        content_str = ' '.join([str(part) for part in parts if part is not None])
                        if len(content_str) > 100:
                            content_str = content_str[:97] + "..."
                    except Exception:
                        content_str = "[content error]"
                    
                    # Color based on role
                    role_color = {
                        'user': 'green',
                        'assistant': 'blue',
                        'system': 'yellow',
                        'tool': 'magenta'
                    }.get(role, 'white')
                    
                    # Display message with proper indentation
                    indent = "  " * depth
                    console.print(f"{indent}[{role_color}]{role}[/{role_color}] ({content_type}): {content_str}")
                except Exception as e:
                    # Safely show error without crashing
                    msg_id = msg.get('id', 'unknown')
                    console.print(f"  [red]Error displaying message {msg_id}: {str(e)}[/red]")
            
            # Get media references
            media_refs = accessor.get_media_references(conversation)
            
            if media_refs:
                console.print(f"\n[bold]Media references ({len(media_refs)}):[/bold]")
                
                table = Table()
                table.add_column("Name")
                table.add_column("ID", style="cyan")
                table.add_column("Type", style="yellow")
                
                if verify_media:
                    table.add_column("In Archive", style="green")
                
                for ref in media_refs:
                    row = [
                        ref['name'],
                        ref['id'],
                        ref['mime_type'],
                    ]
                    
                    if verify_media:
                        media_path = accessor.find_media_file_by_id(ref['id'])
                        row.append("✓" if media_path else "✗")
                    
                    table.add_row(*row)
                
                console.print(table)
        
        # Verify against database if requested
        if verify_database:
            verify_against_database(conversation, media_refs if not metadata_only else [])
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

@app.command("extract-media")
def extract_media(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
    file_id: str = typer.Argument(..., help="ID of the media file to extract"),
    output_dir: Path = typer.Option(None, "--output", "-o", help="Directory to extract to (defaults to temp dir)"),
):
    """Extract a specific media file from the archive."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        
        # Find the file in the archive
        media_path = accessor.find_media_file_by_id(file_id)
        
        if not media_path:
            console.print(f"[bold red]Error:[/bold red] Media file with ID '{file_id}' not found")
            sys.exit(1)
        
        # Determine output directory
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # Extract the file
        extracted_path = accessor.extract_media_file(media_path, str(output_dir))
        
        console.print(f"[bold green]Successfully extracted:[/bold green] {extracted_path}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

@app.command("search")
def search_messages(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
    query: str = typer.Argument(..., help="Text to search for in messages"),
    limit: int = typer.Option(10, "--limit", "-n", help="Maximum number of results to show"),
):
    """Search for messages containing specific text."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        results = accessor.search_messages(query)
        
        console.print(f"[bold]Found {len(results)} messages containing '{query}'[/bold]")
        
        if not results:
            return
        
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Conversation ID", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Content")
        
        for i, (conv_id, message) in enumerate(results[:limit]):
            role = message.get('author', {}).get('role', 'unknown')
            content = message.get('content', {})
            parts = content.get('parts', [])
            
            # Format content
            content_str = ' '.join([str(part) for part in parts])
            if len(content_str) > 100:
                content_str = content_str[:97] + "..."
            
            table.add_row(conv_id, role, content_str)
        
        console.print(table)
        
        if len(results) > limit:
            console.print(f"\nShowing {limit} of {len(results)} results. Use --limit to show more.")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

@app.command("list-media")
def list_media(
    archive_path: Path = typer.Argument(..., help="Path to the archive zip file"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of media items to show"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, csv, json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save output to file"),
    show_all_references: bool = typer.Option(False, "--all-refs", help="Show all references for each file"),
    media_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by media type (e.g., 'generated', 'uploaded')"),
    role: Optional[str] = typer.Option(None, "--role", "-r", help="Filter by message role (e.g., 'tool', 'user', 'assistant')"),
):
    """List media files in the archive with their message associations."""
    try:
        accessor = ArchiveAccessor(str(archive_path))
        media_mapping = accessor.get_media_mapping()
        
        console.print(f"[bold]Found {len(media_mapping)} media files in archive[/bold]")
        
        # Apply filtering
        if role:
            # Filter by message role (with comprehensive None checking)
            filtered_mapping = []
            for item in media_mapping:
                if not item or not isinstance(item, dict) or 'references' not in item:
                    continue
                
                # Safe reference filtering
                matching_refs = []
                for ref in item.get('references', []):
                    if ref and isinstance(ref, dict) and ref.get('role') == role:
                        matching_refs.append(ref)
                
                if matching_refs:
                    # Create a new item with only matching references
                    try:
                        new_item = item.copy()
                        new_item['references'] = matching_refs
                        filtered_mapping.append(new_item)
                    except (TypeError, AttributeError):
                        # Skip items that can't be processed
                        pass
            
            media_mapping = filtered_mapping
            console.print(f"[bold]Found {len(media_mapping)} files with {role} role references[/bold]")
                
        if media_type:
            # Basic type filter (with None checking)
            filtered_type_mapping = []
            
            if media_type.lower() == 'generated':
                # Only show generated images (DALL-E)
                for item in media_mapping:
                    if item and isinstance(item, dict) and 'path' in item:
                        path = item.get('path', '')
                        if path and isinstance(path, str) and ('dalle-generations' in path or path.endswith('.webp')):
                            filtered_type_mapping.append(item)
                console.print(f"[bold]Found {len(filtered_type_mapping)} generated image files[/bold]")
            elif media_type.lower() == 'uploaded':
                # Only show uploaded media
                for item in media_mapping:
                    if item and isinstance(item, dict) and 'path' in item:
                        path = item.get('path', '')
                        if path and isinstance(path, str) and 'dalle-generations' not in path and not path.endswith('.webp'):
                            filtered_type_mapping.append(item)
                console.print(f"[bold]Found {len(filtered_type_mapping)} uploaded media files[/bold]")
            else:
                # Keep all items if no valid filter
                filtered_type_mapping = media_mapping
                
            media_mapping = filtered_type_mapping
        
        # Filter out items with no references if requested (with None checking)
        if not show_all_references:
            filtered_refs = []
            for item in media_mapping:
                if (item and isinstance(item, dict) and 
                    'references' in item and 
                    item['references'] and 
                    isinstance(item['references'], list) and 
                    len(item['references']) > 0):
                    filtered_refs.append(item)
            media_mapping = filtered_refs
            console.print(f"[bold]{len(media_mapping)} files have message references[/bold]")
        
        if not media_mapping:
            return
            
        # Format as requested
        if format.lower() == "json":
            # JSON output
            output_data = media_mapping[:limit]
            if output:
                with open(output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                console.print(f"[green]Saved JSON output to {output}[/green]")
            else:
                console.print(json.dumps(output_data, indent=2))
                
        elif format.lower() == "csv":
            # CSV output
            import csv
            
            # Flatten the data for CSV
            flattened_data = []
            for item in media_mapping[:limit]:
                if not item['references']:
                    # Add one row with empty reference data
                    flattened_data.append({
                        'path': item['path'],
                        'filename': item['filename'],
                        'file_id': item['file_id'] or '',
                        'conversation_id': '',
                        'message_id': '',
                        'role': '',
                        'assistant_parent_id': '',
                        'file_name': '',
                        'mime_type': ''
                    })
                else:
                    # Add a row for each reference
                    for ref in item['references']:
                        # Get assistant parent ID if available (with proper None checking)
                        assistant_msg_id = ''
                        if ref and isinstance(ref, dict):
                            assistant_msg_id = ref.get('assistant_parent_id', '')
                            # For user uploads, there's no assistant parent
                            if ref.get('role') == 'user':
                                assistant_msg_id = ''
                            
                        # Safely get values with fallbacks for None cases
                        conversation_id = ''
                        message_id = ''
                        role = ''
                        file_name = ''
                        mime_type = ''
                        
                        if ref and isinstance(ref, dict):
                            conversation_id = ref.get('conversation_id', '')
                            message_id = ref.get('message_id', '')
                            role = ref.get('role', '')
                            file_name = ref.get('file_name', '')
                            mime_type = ref.get('mime_type', '')
                        
                        flattened_data.append({
                            'path': item['path'],
                            'filename': item['filename'],
                            'file_id': item['file_id'] or '',
                            'conversation_id': conversation_id,
                            'message_id': message_id,
                            'role': role,
                            'assistant_parent_id': assistant_msg_id,
                            'file_name': file_name,
                            'mime_type': mime_type
                        })
            
            # Write CSV
            fieldnames = ['path', 'filename', 'file_id', 'conversation_id', 
                         'message_id', 'role', 'assistant_parent_id', 'file_name', 'mime_type']
            
            if output:
                with open(output, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(flattened_data)
                console.print(f"[green]Saved CSV output to {output}[/green]")
            else:
                # For stdout, use a StringIO buffer
                import io
                output_buffer = io.StringIO()
                writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened_data)
                console.print(output_buffer.getvalue())
                
        else:
            # Default table output
            table = Table(title=f"Media Files in {archive_path.name}")
            table.add_column("Path", style="cyan", width=30)
            table.add_column("File ID", style="green", width=20)
            table.add_column("Conv ID", width=20)
            table.add_column("Message ID", width=20)
            table.add_column("Role", style="magenta", width=10)
            table.add_column("Assistant Msg ID", style="blue", width=20)
            table.add_column("Original Name", width=30)
            
            for item in media_mapping[:limit]:
                if not item['references']:
                    # Display files with no references
                    file_path = item['path']
                    if len(file_path) > 30:
                        file_path = "..." + file_path[-27:]
                        
                    table.add_row(
                        file_path, 
                        item['file_id'] or "-",
                        "-", "-", "-", "-", "-"
                    )
                else:
                    # Display the first reference (with safety checks)
                    first_ref = None
                    if item['references'] and len(item['references']) > 0:
                        first_ref = item['references'][0]
                    
                    file_path = item['path']
                    if len(file_path) > 30:
                        file_path = "..." + file_path[-27:]
                    
                    # Default values    
                    original_name = '-'
                    assistant_msg_id = '-'
                    role = '-'
                    message_id = '-'
                    conversation_id = '-'
                    
                    # Extract values if reference exists
                    if first_ref and isinstance(first_ref, dict):
                        original_name = first_ref.get('file_name', '-')
                        if len(original_name) > 30:
                            original_name = original_name[:27] + "..."
                        
                        # Get assistant parent info for DALL-E images
                        assistant_msg_id = first_ref.get('assistant_parent_id', '-')
                        # For user uploads, there's no assistant parent
                        role = first_ref.get('role', '-')
                        if role == 'user':
                            assistant_msg_id = '-'
                            
                        message_id = first_ref.get('message_id', '-')
                        conversation_id = first_ref.get('conversation_id', '-')
                        
                    table.add_row(
                        file_path,
                        item['file_id'] or "-",
                        conversation_id,
                        message_id,
                        role,
                        assistant_msg_id,
                        original_name
                    )
                    
                    # Display additional references if requested
                    if show_all_references and item['references'] and len(item['references']) > 1:
                        for ref in item['references'][1:]:
                            if not ref or not isinstance(ref, dict):
                                continue
                                
                            # Get reference values with safety checks
                            ref_assistant_id = ref.get('assistant_parent_id', '-')
                            ref_role = ref.get('role', '-')
                            if ref_role == 'user':
                                ref_assistant_id = '-'
                                
                            ref_conv_id = ref.get('conversation_id', '-')
                            ref_msg_id = ref.get('message_id', '-')
                            ref_file_name = ref.get('file_name', '-')
                            
                            table.add_row(
                                "", "",  # Empty path, file_id columns
                                ref_conv_id,
                                ref_msg_id,
                                ref_role,
                                ref_assistant_id,
                                ref_file_name
                            )
            
            if output:
                with open(output, 'w') as f:
                    f.write(str(table))
                console.print(f"[green]Saved table output to {output}[/green]")
            else:
                console.print(table)
        
        if len(media_mapping) > limit:
            console.print(f"\nShowing {limit} of {len(media_mapping)} items. Use --limit to show more.")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)

def verify_against_database(conversation: dict, media_refs: list):
    """Verify conversation and media against database entries."""
    console.print("\n[bold]Verifying against database...[/bold]")
    
    conv_id = conversation.get('conversation_id')
    
    with get_session() as session:
        # Check if conversation exists in database
        db_conv = session.query(Conversation).filter(Conversation.source_conversation_id == conv_id).first()
        
        if not db_conv:
            console.print(f"[bold red]✗[/bold red] Conversation '{conv_id}' not found in database")
            return
        
        console.print(f"[bold green]✓[/bold green] Found conversation in database: ID={db_conv.id}")
        
        # Check messages
        mapping = conversation.get('mapping', {})
        db_messages = session.query(Message).filter(Message.conversation_id == db_conv.id).all()
        
        console.print(f"Archive has {len(mapping)} messages, database has {len(db_messages)} messages")
        
        # Check media
        if media_refs:
            for ref in media_refs:
                # Try to find media in database by original file ID
                db_media = session.query(Media).filter(Media.original_file_id.like(f"%{ref['id']}%")).first()
                
                if db_media:
                    console.print(f"[bold green]✓[/bold green] Media '{ref['name']}' found in database: ID={db_media.id}, Path={db_media.file_path}")
                else:
                    console.print(f"[bold red]✗[/bold red] Media '{ref['name']}' (ID: {ref['id']}) not found in database")