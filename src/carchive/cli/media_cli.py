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
            # Add the "file-" prefix back to match how it's stored in the database
            original_file_id = f"file-{file_id}"
            
            # Debug info for original_file_id matching
            typer.echo(f"Looking for media with original_file_id: {original_file_id}")
            existing_media_count = session.query(Media).filter(
                Media.original_file_id == original_file_id
            ).count()
            typer.echo(f"Found {existing_media_count} matching media entries")
            
            # Check if the media is already in the database by comparing original_file_id
            # This handles cases where the media was previously imported to a different path
            existing_media = session.query(Media).filter(
                Media.original_file_id == original_file_id
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
            
            # Determine mime type from the extension - define this BEFORE we use it in multiple places
            ext_to_mime = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png', 
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.avif': 'image/avif',
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.ogg': 'audio/ogg',
                '.flac': 'audio/flac',
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.avi': 'video/x-msvideo',
                '.webm': 'video/webm',
                '.pdf': 'application/pdf'
            }
            mime_type = ext_to_mime.get(ext, 'application/octet-stream')
            
            if not existing_media:
                # Create a new media entry
                
                # Get file size in bytes
                file_size = file_path.stat().st_size if file_path.exists() else None
                
                # Get absolute file path for storage
                absolute_file_path = str(file_path.absolute())
                
                new_media = Media(
                    id=uuid.uuid4(),
                    file_path=absolute_file_path,
                    media_type=media_type,
                    mime_type=mime_type,
                    file_size=file_size,
                    original_file_id=original_file_id,  # Use the corrected ID with the "file-" prefix
                    original_file_name=remaining_name,
                    is_generated=is_generated
                )
                
                if not dry_run:
                    session.add(new_media)
                    session.flush()  # To get the ID
                    media_id = new_media.id
                else:
                    media_id = "WOULD_CREATE_ID"
                
                # Use just the file path string for display to avoid relative_to issues
                typer.echo(f"Created media entry: {media_id} for {file_path}")
                updated_count += 1
            else:
                # Update existing media
                media_id = existing_media.id
                
                # Determine if we need to update any fields
                needs_update = False
                update_fields = []
                
                # Check what needs to be updated
                if existing_media.original_file_id != original_file_id:
                    needs_update = True
                    update_fields.append("original_file_id")
                    if not dry_run:
                        existing_media.original_file_id = original_file_id
                
                if existing_media.original_file_name != remaining_name:
                    needs_update = True
                    update_fields.append("original_file_name")
                    if not dry_run:
                        existing_media.original_file_name = remaining_name
                
                if existing_media.is_generated != is_generated:
                    needs_update = True
                    update_fields.append("is_generated")
                    if not dry_run:
                        existing_media.is_generated = is_generated
                
                # Check if mime_type needs update (mime_type already calculated above)
                if getattr(existing_media, 'mime_type', None) != mime_type:
                    needs_update = True
                    update_fields.append("mime_type")
                    if not dry_run:
                        existing_media.mime_type = mime_type
                
                # Check if file_size needs update
                file_size = file_path.stat().st_size if file_path.exists() else None
                if getattr(existing_media, 'file_size', None) != file_size:
                    needs_update = True
                    update_fields.append("file_size")
                    if not dry_run:
                        existing_media.file_size = file_size
                
                if needs_update:
                    typer.echo(f"Updated media entry: {media_id} (fields: {', '.join(update_fields)})")
                    updated_count += 1
                else:
                    typer.echo(f"No updates needed for media: {media_id}")
            
            # Find messages that reference this file ID
            referencing_messages = session.query(Message).filter(
                Message.content.ilike(f"%{original_file_id}%")
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
                                    # Create MessageMedia association instead of setting message_id
                                    from carchive.database.models import MessageMedia
                                    
                                    media_id_to_use = existing_media.id if existing_media else new_media.id
                                    
                                    # Check if association already exists
                                    existing_assoc = session.query(MessageMedia).filter(
                                        MessageMedia.message_id == msg.id,
                                        MessageMedia.media_id == media_id_to_use
                                    ).first()
                                    
                                    if not existing_assoc:
                                        assoc = MessageMedia(
                                            id=uuid.uuid4(),
                                            message_id=msg.id,
                                            media_id=media_id_to_use,
                                            association_type="uploaded"
                                        )
                                        session.add(assoc)
                                typer.echo(f"Linked user message {msg.id} to media {media_id}")
                                linked_count += 1
                    
                    # For assistant messages that generate images
                    elif role == 'assistant' and is_generated:
                        if not dry_run:
                            # Create MessageMedia association instead of setting linked_message_id
                            from carchive.database.models import MessageMedia
                            
                            media_id_to_use = existing_media.id if existing_media else new_media.id
                            
                            # Check if association already exists
                            existing_assoc = session.query(MessageMedia).filter(
                                MessageMedia.message_id == msg.id,
                                MessageMedia.media_id == media_id_to_use
                            ).first()
                            
                            if not existing_assoc:
                                assoc = MessageMedia(
                                    id=uuid.uuid4(),
                                    message_id=msg.id,
                                    media_id=media_id_to_use,
                                    association_type="generated"
                                )
                                session.add(assoc)
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
        # Get all messages with attached media using MessageMedia association table
        from carchive.database.models import MessageMedia
        
        messages_with_media = session.query(Message).join(
            MessageMedia,
            Message.id == MessageMedia.message_id
        ).all()
        
        updated_count = 0
        for msg in messages_with_media:
            # Get all media attached to this message via MessageMedia association
            attached_media = session.query(Media).join(
                MessageMedia,
                Media.id == MessageMedia.media_id
            ).filter(
                MessageMedia.message_id == msg.id
            ).all()
            
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
                        'name': media.original_file_name,
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
        
        # Query using MessageMedia association table 
        from carchive.database.models import MessageMedia
        
        # Count media that are linked to messages
        media_with_messages = session.query(Media).join(
            MessageMedia, 
            Media.id == MessageMedia.media_id
        ).count()
        
        # Count by association type
        association_types = {}
        from carchive.database.models import MessageMedia
        
        assoc_query = session.query(MessageMedia.association_type, sa.func.count(MessageMedia.id)) \
                            .group_by(MessageMedia.association_type).all()
        
        for assoc_type, count in assoc_query:
            if assoc_type:  # Skip None values
                association_types[assoc_type] = count
        
        # Calculate uploaded vs generated
        user_uploaded = association_types.get('uploaded', 0)
        ai_generated = association_types.get('generated', 0)
        assistant_referenced = association_types.get('assistant_reference', 0)
        
        typer.echo("\nMedia Distribution Analysis:")
        typer.echo(f"- Total media files: {total_media}")
        typer.echo("\nBy Type:")
        for media_type, count in by_type.items():
            typer.echo(f"- {media_type}: {count} ({count/total_media*100:.1f}%)")
        
        typer.echo("\nBy Association Type:")
        for assoc_type, count in association_types.items():
            typer.echo(f"- {assoc_type}: {count} ({count/total_media*100 if total_media else 0:.1f}%)")
        
        typer.echo("\nBy Role:")
        typer.echo(f"- User uploaded: {user_uploaded} ({user_uploaded/total_media*100 if total_media else 0:.1f}%)")
        typer.echo(f"- AI generated: {ai_generated} ({ai_generated/total_media*100 if total_media else 0:.1f}%)")
        typer.echo(f"- Assistant referenced: {assistant_referenced} ({assistant_referenced/total_media*100 if total_media else 0:.1f}%)")

@app.command()
def link_ai_generated_images():
    """
    Link AI-generated images from tool messages to their associated assistant messages.
    
    This is useful for DALL-E and other image generation tools where the image is 
    attached to a tool message but should be displayed with the assistant message
    that requested or references the image.
    """
    from carchive.database.models import MessageMedia
    
    with get_session() as session:
        # Find tool messages with generated images
        tool_messages_with_media = session.query(Message, MessageMedia, Media).join(
            MessageMedia, Message.id == MessageMedia.message_id
        ).join(
            Media, MessageMedia.media_id == Media.id
        ).filter(
            Message.role == 'tool',
            Media.media_type == 'image',
            MessageMedia.association_type == 'generated'
        ).all()
        
        if not tool_messages_with_media:
            typer.echo("No AI-generated images found in tool messages.")
            return
        
        typer.echo(f"Found {len(tool_messages_with_media)} AI-generated images in tool messages.")
        
        linked_count = 0
        
        for tool_message, message_media, media in tool_messages_with_media:
            # Find the parent message for this tool message - typically an assistant message
            if not tool_message.parent_id:
                typer.echo(f"Tool message {tool_message.id} has no parent message, skipping.")
                continue
            
            parent_message = session.query(Message).filter(Message.id == tool_message.parent_id).first()
            if not parent_message:
                typer.echo(f"Parent message {tool_message.parent_id} not found for tool message {tool_message.id}, skipping.")
                continue
            
            if parent_message.role != 'assistant':
                typer.echo(f"Parent message {parent_message.id} is not an assistant message (role: {parent_message.role}), skipping.")
                continue
            
            # Check if there's already an association between the assistant message and this media
            existing_assoc = session.query(MessageMedia).filter(
                MessageMedia.message_id == parent_message.id,
                MessageMedia.media_id == media.id
            ).first()
            
            if existing_assoc:
                typer.echo(f"Assistant message {parent_message.id} already has an association with media {media.id}, skipping.")
                continue
            
            # Create a new association
            new_assoc = MessageMedia(
                id=uuid.uuid4(),
                message_id=parent_message.id,
                media_id=media.id,
                association_type='assistant_reference'
            )
            
            session.add(new_assoc)
            linked_count += 1
        
        if linked_count > 0:
            session.commit()
            typer.echo(f"Successfully linked {linked_count} AI-generated images to assistant messages.")
        else:
            typer.echo("No new links were created.")
            
@app.command()
def find(
    media_type: str = typer.Option("image", help="Type of media to filter by (e.g., 'image', 'pdf')"),
    limit: int = typer.Option(10, help="Maximum number of results to return"),
    association_type: Optional[str] = typer.Option(None, help="Filter by association type (e.g., 'uploaded', 'generated', 'assistant_reference')"),
    search_term: Optional[str] = typer.Option(None, help="Optional text to search for in file paths or names"),
    show_messages: bool = typer.Option(True, help="Show associated messages"),
    show_conversations: bool = typer.Option(True, help="Show conversation titles for associated messages"),
    format: str = typer.Option("table", help="Output format: table, json")
):
    """
    Find media items and their associated messages.
    
    This command helps you locate media files in the database along with the messages
    they are associated with. Useful for finding images, PDFs, or other media files.
    """
    from carchive.database.models import MessageMedia, Conversation
    import json
    
    with get_session() as session:
        # Build the query for media items
        query = session.query(Media).filter(Media.media_type == media_type)
        
        # Apply additional filters if provided
        if search_term:
            search_pattern = f"%{search_term}%"
            query = query.filter(
                sa.or_(
                    Media.file_path.ilike(search_pattern),
                    Media.original_file_name.ilike(search_pattern),
                    Media.original_file_id.ilike(search_pattern)
                )
            )
        
        # If association_type is specified, join with MessageMedia to filter
        if association_type:
            query = query.join(MessageMedia, Media.id == MessageMedia.media_id)
            query = query.filter(MessageMedia.association_type == association_type)
        
        # Order by creation date (newest first) and apply limit
        query = query.order_by(Media.created_at.desc()).limit(limit)
        
        # Execute query
        media_items = query.all()
        
        if not media_items:
            typer.echo(f"No {media_type} media items found matching your criteria.")
            return
        
        typer.echo(f"Found {len(media_items)} {media_type} items")
        
        # Prepare results based on format
        if format == "json":
            results = []
            
            for media in media_items:
                media_data = {
                    "id": str(media.id),
                    "file_path": media.file_path,
                    "media_type": media.media_type,
                    "original_file_id": media.original_file_id,
                    "original_file_name": media.original_file_name,
                    "is_generated": media.is_generated,
                    "created_at": str(media.created_at)
                }
                
                # If requested, include associated messages
                if show_messages:
                    message_assocs = session.query(MessageMedia, Message).join(
                        Message, MessageMedia.message_id == Message.id
                    ).filter(
                        MessageMedia.media_id == media.id
                    ).all()
                    
                    media_data["messages"] = []
                    
                    for assoc, message in message_assocs:
                        message_data = {
                            "id": str(message.id),
                            "role": message.role,
                            "association_type": assoc.association_type,
                            "content_preview": (message.content[:100] + "...") if message.content and len(message.content) > 100 else message.content
                        }
                        
                        # Include conversation info if requested
                        if show_conversations and message.conversation_id:
                            conversation = session.query(Conversation).filter(
                                Conversation.id == message.conversation_id
                            ).first()
                            
                            if conversation:
                                message_data["conversation"] = {
                                    "id": str(conversation.id),
                                    "title": conversation.title
                                }
                        
                        media_data["messages"].append(message_data)
                
                results.append(media_data)
            
            # Print JSON output
            typer.echo(json.dumps(results, indent=2))
        
        else:  # Table format
            # For table format, we'll use a simpler approach
            for i, media in enumerate(media_items, 1):
                typer.echo(f"\n{i}. Media ID: {media.id}")
                typer.echo(f"   Type: {media.media_type}")
                typer.echo(f"   Path: {media.file_path}")
                typer.echo(f"   Original name: {media.original_file_name}")
                typer.echo(f"   Original ID: {media.original_file_id}")
                typer.echo(f"   Created: {media.created_at}")
                
                if show_messages:
                    message_assocs = session.query(MessageMedia, Message).join(
                        Message, MessageMedia.message_id == Message.id
                    ).filter(
                        MessageMedia.media_id == media.id
                    ).all()
                    
                    if message_assocs:
                        typer.echo("\n   Associated Messages:")
                        for j, (assoc, message) in enumerate(message_assocs, 1):
                            typer.echo(f"     {j}. Message ID: {message.id}")
                            typer.echo(f"        Role: {message.role}")
                            typer.echo(f"        Association: {assoc.association_type}")
                            
                            # Include conversation info if requested
                            if show_conversations and message.conversation_id:
                                conversation = session.query(Conversation).filter(
                                    Conversation.id == message.conversation_id
                                ).first()
                                
                                if conversation:
                                    typer.echo(f"        Conversation: {conversation.title} ({conversation.id})")
                            
                            # Show a preview of the message content
                            if message.content:
                                preview = message.content.replace("\n", " ")[:50]
                                typer.echo(f"        Content: {preview}...")
                    else:
                        typer.echo("\n   No associated messages found")
                
                typer.echo("   " + "-" * 50)
                
@app.command()
def find_conversations(
    media_type: str = typer.Option("image", help="Type of media to filter by (e.g., 'image', 'pdf')"),
    limit: int = typer.Option(10, help="Maximum number of conversations to return"),
    association_type: Optional[str] = typer.Option(None, help="Filter by association type (e.g., 'uploaded', 'generated', 'assistant_reference')"),
    format: str = typer.Option("table", help="Output format: table, json")
):
    """
    Find conversations containing specific types of media.
    
    This command helps you locate conversations that contain images, PDFs, or other
    media files. Useful for finding conversations with visual content.
    """
    from carchive.database.models import MessageMedia, Conversation
    import json
    
    with get_session() as session:
        # Build a query that finds conversations with the specified media type
        # We need to join several tables: Media -> MessageMedia -> Message -> Conversation
        query = session.query(Conversation, sa.func.count(Media.id).label('media_count')).join(
            Message, Message.conversation_id == Conversation.id
        ).join(
            MessageMedia, MessageMedia.message_id == Message.id
        ).join(
            Media, Media.id == MessageMedia.media_id
        ).filter(
            Media.media_type == media_type
        )
        
        # Apply association_type filter if specified
        if association_type:
            query = query.filter(MessageMedia.association_type == association_type)
        
        # Group by conversation and order by media count (most media first)
        query = query.group_by(Conversation.id).order_by(sa.desc('media_count')).limit(limit)
        
        # Execute query
        conversation_results = query.all()
        
        if not conversation_results:
            typer.echo(f"No conversations found with {media_type} media.")
            return
        
        typer.echo(f"Found {len(conversation_results)} conversations with {media_type} media")
        
        # Format results
        if format == "json":
            results = []
            
            for conversation, media_count in conversation_results:
                # Get some details about the media in this conversation
                media_details = session.query(Media).join(
                    MessageMedia, Media.id == MessageMedia.media_id
                ).join(
                    Message, MessageMedia.message_id == Message.id
                ).filter(
                    Message.conversation_id == conversation.id,
                    Media.media_type == media_type
                ).all()
                
                result = {
                    "conversation_id": str(conversation.id),
                    "title": conversation.title,
                    "media_count": media_count,
                    "created_at": str(conversation.created_at),
                    "media_items": [
                        {
                            "id": str(media.id),
                            "type": media.media_type,
                            "original_name": media.original_file_name
                        }
                        for media in media_details[:5]  # Limit to first 5 for brevity
                    ]
                }
                
                results.append(result)
            
            # Print JSON output
            typer.echo(json.dumps(results, indent=2))
            
        else:  # Table format
            for i, (conversation, media_count) in enumerate(conversation_results, 1):
                typer.echo(f"\n{i}. Conversation: {conversation.title or '(Untitled)'}")
                typer.echo(f"   ID: {conversation.id}")
                typer.echo(f"   Media count: {media_count}")
                typer.echo(f"   Created: {conversation.created_at}")
                
                # Get a sample of the media in this conversation
                media_details = session.query(Media, Message.role).join(
                    MessageMedia, Media.id == MessageMedia.media_id
                ).join(
                    Message, MessageMedia.message_id == Message.id
                ).filter(
                    Message.conversation_id == conversation.id,
                    Media.media_type == media_type
                ).limit(3).all()
                
                if media_details:
                    typer.echo("\n   Sample media:")
                    for j, (media, role) in enumerate(media_details, 1):
                        typer.echo(f"     {j}. {media.original_file_name or media.id} (in {role} message)")
                
                typer.echo("   " + "-" * 50)
                
@app.command()
def find_gpt_generated(
    limit: int = typer.Option(10, help="Maximum number of results to return"),
    gpt_name: Optional[str] = typer.Option(None, help="Filter by specific GPT name (e.g., 'DALL-E')"),
    format: str = typer.Option("table", help="Output format: table, json"),
    show_messages: bool = typer.Option(True, help="Show associated messages")
):
    """
    Find media generated by GPTs (like DALL-E) and their associated conversations.
    
    This command helps you locate AI-generated images and other media files created
    by GPTs like DALL-E. The command can filter by specific GPT names and show
    associated messages and conversations.
    """
    from carchive.database.models import MessageMedia, Conversation
    import json
    
    with get_session() as session:
        # Start with basic query on media items that are marked as generated
        query = session.query(Media).filter(Media.is_generated == True)
        
        # Optional GPT name filter
        if gpt_name:
            # Look for GPT name in meta_info or in message content
            query = query.join(
                MessageMedia, Media.id == MessageMedia.media_id
            ).join(
                Message, MessageMedia.message_id == Message.id
            ).filter(
                sa.or_(
                    Message.content.ilike(f"%{gpt_name}%"),
                    sa.cast(Message.meta_info, sa.String).ilike(f"%{gpt_name}%")
                )
            )
        
        # Order by creation time (newest first) and limit results
        query = query.order_by(Media.created_at.desc()).limit(limit)
        
        # Execute query
        gpt_media = query.all()
        
        if not gpt_media:
            typer.echo("No GPT-generated media found.")
            return
        
        typer.echo(f"Found {len(gpt_media)} GPT-generated media items")
        
        # Format results based on output format
        if format == "json":
            results = []
            
            for media in gpt_media:
                media_data = {
                    "id": str(media.id),
                    "file_path": media.file_path,
                    "media_type": media.media_type,
                    "original_file_name": media.original_file_name,
                    "created_at": str(media.created_at)
                }
                
                # If requested, include associated messages
                if show_messages:
                    # Find messages that reference or are associated with this media
                    message_assocs = session.query(MessageMedia, Message).join(
                        Message, MessageMedia.message_id == Message.id
                    ).filter(
                        MessageMedia.media_id == media.id
                    ).all()
                    
                    media_data["messages"] = []
                    
                    for assoc, message in message_assocs:
                        # For each message, check if it has a conversation
                        conversation_info = None
                        if message.conversation_id:
                            conversation = session.query(Conversation).filter(
                                Conversation.id == message.conversation_id
                            ).first()
                            
                            if conversation:
                                conversation_info = {
                                    "id": str(conversation.id),
                                    "title": conversation.title
                                }
                        
                        # Add message data
                        message_data = {
                            "id": str(message.id),
                            "role": message.role,
                            "association_type": assoc.association_type,
                            "conversation": conversation_info,
                            "content_preview": (message.content[:100] + "...") if message.content and len(message.content) > 100 else message.content
                        }
                        
                        media_data["messages"].append(message_data)
                
                results.append(media_data)
            
            # Print JSON output
            typer.echo(json.dumps(results, indent=2))
            
        else:  # Table format
            for i, media in enumerate(gpt_media, 1):
                typer.echo(f"\n{i}. GPT-Generated Media: {media.original_file_name or media.id}")
                typer.echo(f"   ID: {media.id}")
                typer.echo(f"   Type: {media.media_type}")
                typer.echo(f"   Path: {media.file_path}")
                typer.echo(f"   Created: {media.created_at}")
                
                if show_messages:
                    # Find messages that reference or are associated with this media
                    message_assocs = session.query(MessageMedia, Message).join(
                        Message, MessageMedia.message_id == Message.id
                    ).filter(
                        MessageMedia.media_id == media.id
                    ).all()
                    
                    if message_assocs:
                        typer.echo("\n   Associated Messages:")
                        for j, (assoc, message) in enumerate(message_assocs, 1):
                            typer.echo(f"     {j}. Message: {message.id}")
                            typer.echo(f"        Role: {message.role}")
                            typer.echo(f"        Association: {assoc.association_type}")
                            
                            # Show conversation if available
                            if message.conversation_id:
                                conversation = session.query(Conversation).filter(
                                    Conversation.id == message.conversation_id
                                ).first()
                                
                                if conversation:
                                    typer.echo(f"        Conversation: {conversation.title or '(Untitled)'} ({conversation.id})")
                            
                            # Show content preview
                            if message.content:
                                # Look for GPT name references in the content
                                content_preview = message.content.replace("\n", " ")[:100]
                                typer.echo(f"        Content: {content_preview}...")
                    else:
                        typer.echo("\n   No associated messages found")
                
                typer.echo("   " + "-" * 50)