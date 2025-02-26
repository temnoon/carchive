# src/carchive/cli/media_cli.py

import typer
import os
import re
import uuid
import logging
import sqlalchemy as sa
from typing import Optional, List
from pathlib import Path

from carchive.database.session import get_session
from carchive.database.models import Media, Message, Conversation

app = typer.Typer(name="media", help="Commands for managing media files")
logger = logging.getLogger(__name__)

@app.command()
def scan_and_link(
    chat_folder: str = typer.Option("chat", help="Path to the chat folder containing media files"),
    dry_run: bool = typer.Option(False, help="Only show what would be done without making changes"),
    limit: int = typer.Option(0, help="Limit the number of files to process (0 for all)")
):
    """
    Scan the media files in the chat folder, extract their IDs, and link them to messages in the database.
    
    This command uses the correlation logic from test_correlate_user_prompt_and_assistant_transcript3.py.
    """
    chat_path = Path(chat_folder)
    if not chat_path.exists():
        typer.echo(f"Error: Chat folder {chat_folder} does not exist.")
        raise typer.Exit(1)
    
    # Patterns for extracting file IDs
    file_dash_pattern = re.compile(r"^file-([^-]+)-(.+)$")
    
    # Get all media files
    media_files = list(chat_path.rglob("*"))
    media_files = [f for f in media_files if f.is_file() and not f.name.startswith('.')]
    
    if limit > 0:
        media_files = media_files[:limit]
    
    typer.echo(f"Found {len(media_files)} media files in {chat_folder}")
    
    # Process each file
    processed_count = 0
    updated_count = 0
    linked_count = 0
    
    for file_path in media_files:
        processed_count += 1
        if processed_count % 100 == 0:
            typer.echo(f"Processed {processed_count}/{len(media_files)} files...")
        
        file_name = file_path.name
        match = file_dash_pattern.match(file_name)
        
        if not match:
            continue
        
        file_id = match.group(1)
        remaining_name = match.group(2)
        
        with get_session() as session:
            # Check if the media is already in the database
            existing_media = session.query(Media).filter(
                Media.file_path == str(file_path.relative_to(Path.cwd()))
            ).first()
            
            # Determine media type
            ext = file_path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']:
                media_type = 'image'
            elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
                media_type = 'audio'
            elif ext in ['.mp4', '.mov', '.avi', '.webm']:
                media_type = 'video'
            elif ext in ['.pdf']:
                media_type = 'pdf'
            else:
                media_type = 'other'
            
            # Is this a DALL-E generation?
            is_generated = 'dalle-generations' in str(file_path)
            
            if not existing_media:
                # Create a new media entry
                new_media = Media(
                    id=uuid.uuid4(),
                    file_path=str(file_path.relative_to(Path.cwd())),
                    media_type=media_type,
                    original_file_id=file_id,
                    file_name=file_name,
                    is_generated=is_generated
                )
                
                if not dry_run:
                    session.add(new_media)
                    session.flush()  # To get the ID
                    media_id = new_media.id
                else:
                    media_id = "WOULD_CREATE_ID"
                
                typer.echo(f"Created media entry: {media_id} for {file_path.relative_to(Path.cwd())}")
                updated_count += 1
            else:
                # Update existing media
                media_id = existing_media.id
                
                if existing_media.original_file_id != file_id or existing_media.file_name != file_name:
                    if not dry_run:
                        existing_media.original_file_id = file_id
                        existing_media.file_name = file_name
                        existing_media.is_generated = is_generated
                    typer.echo(f"Updated media entry: {media_id}")
                    updated_count += 1
            
            # Find messages that reference this file ID
            referencing_messages = session.query(Message).filter(
                Message.content.ilike(f"%{file_id}%")
            ).all()
            
            # For each referencing message, find if it's a user upload or assistant generation
            for msg in referencing_messages:
                if msg.meta_info and 'author_role' in msg.meta_info:
                    role = msg.meta_info.get('author_role', '').lower()
                    
                    # For user messages with attachments
                    if role == 'user' and msg.meta_info.get('attachments'):
                        attachments = msg.meta_info.get('attachments', [])
                        for att in attachments:
                            if att.get('id') == file_id:
                                if not dry_run:
                                    if existing_media:
                                        existing_media.message_id = msg.id
                                    else:
                                        new_media.message_id = msg.id
                                typer.echo(f"Linked user message {msg.id} to media {media_id}")
                                linked_count += 1
                    
                    # For assistant messages that generate images
                    elif role == 'assistant' and is_generated:
                        if not dry_run:
                            if existing_media:
                                existing_media.linked_message_id = msg.id
                            else:
                                new_media.linked_message_id = msg.id
                        typer.echo(f"Linked assistant message {msg.id} to generated media {media_id}")
                        linked_count += 1
            
            if not dry_run:
                session.commit()
            
    typer.echo(f"\nSummary:")
    typer.echo(f"- Processed {processed_count} media files")
    typer.echo(f"- Created/Updated {updated_count} media entries")
    typer.echo(f"- Linked {linked_count} messages to media files")
    
    if dry_run:
        typer.echo("\nThis was a dry run. No changes were made to the database.")

@app.command()
def update_message_attachments():
    """
    Update message meta_info to include references to media files that are linked to the message.
    """
    with get_session() as session:
        # Get all messages with attached media
        messages_with_media = session.query(Message).filter(
            Message.id.in_(
                session.query(Media.message_id).filter(Media.message_id.isnot(None))
            )
        ).all()
        
        updated_count = 0
        for msg in messages_with_media:
            # Get all media attached to this message
            attached_media = session.query(Media).filter(Media.message_id == msg.id).all()
            
            # Update meta_info
            if not msg.meta_info:
                msg.meta_info = {}
            
            # Ensure attachments list exists
            if 'attachments' not in msg.meta_info:
                msg.meta_info['attachments'] = []
            
            # Add media info if not already present
            attachments = msg.meta_info['attachments']
            existing_ids = {att.get('id') for att in attachments if att.get('id')}
            
            for media in attached_media:
                if media.original_file_id and media.original_file_id not in existing_ids:
                    attachments.append({
                        'id': media.original_file_id,
                        'name': media.file_name,
                        'media_id': str(media.id),
                        'media_type': media.media_type
                    })
                    updated_count += 1
            
            # Save changes
            msg.meta_info['attachments'] = attachments
        
        session.commit()
        typer.echo(f"Updated {updated_count} attachment references in {len(messages_with_media)} messages")

@app.command()
def analyze_media_distribution():
    """
    Analyze the distribution of media files by type and role.
    """
    with get_session() as session:
        total_media = session.query(Media).count()
        by_type = {}
        media_types = session.query(Media.media_type, sa.func.count(Media.id)).group_by(Media.media_type).all()
        for media_type, count in media_types:
            by_type[media_type] = count
        
        user_uploaded = session.query(Media).filter(Media.message_id.isnot(None)).count()
        ai_generated = session.query(Media).filter(Media.is_generated == True).count()
        
        typer.echo("\nMedia Distribution Analysis:")
        typer.echo(f"- Total media files: {total_media}")
        typer.echo("\nBy Type:")
        for media_type, count in by_type.items():
            typer.echo(f"- {media_type}: {count} ({count/total_media*100:.1f}%)")
        
        typer.echo("\nBy Role:")
        typer.echo(f"- User uploaded: {user_uploaded} ({user_uploaded/total_media*100 if total_media else 0:.1f}%)")
        typer.echo(f"- AI generated: {ai_generated} ({ai_generated/total_media*100 if total_media else 0:.1f}%)")