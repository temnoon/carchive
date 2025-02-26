#!/usr/bin/env python3
# scripts/process_media.py

"""
Process media files to link them with messages.

This script scans the chat folder for media files, extracts their IDs, and links them
to the appropriate messages in the database.
"""

import os
import re
import uuid
from pathlib import Path
import logging
import sys
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from carchive.database.session import get_session
from carchive.database.models import Media, Message, Conversation
from sqlalchemy import func

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def scan_media_files(chat_folder, limit=0):
    """
    Scan the chat folder for media files and return their information.
    """
    chat_path = Path(chat_folder)
    if not chat_path.exists():
        logger.error(f"Chat folder {chat_folder} does not exist")
        return []
    
    # Get all media files
    media_files = []
    for file_path in chat_path.rglob("*"):
        if not file_path.is_file() or file_path.name.startswith('.'):
            continue
        
        # Extract file information
        file_info = {
            'path': file_path,
            'relative_path': str(file_path),  # Store the path as is
            'name': file_path.name,
            'is_generated': 'dalle-generations' in str(file_path)
        }
        
        # Extract file ID
        file_dash_pattern = re.compile(r"^file-([^-]+)-(.+)$")
        match = file_dash_pattern.match(file_path.name)
        
        if match:
            file_info['file_id'] = match.group(1)
            file_info['remainder'] = match.group(2)
            media_files.append(file_info)
    
    logger.info(f"Found {len(media_files)} media files in {chat_folder}")
    
    if limit > 0:
        media_files = media_files[:limit]
        logger.info(f"Processing limited set of {limit} files")
    
    return media_files

def get_media_type(file_path):
    """
    Determine the media type based on file extension.
    """
    ext = file_path.suffix.lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']:
        return 'image'
    elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
        return 'audio'
    elif ext in ['.mp4', '.mov', '.avi', '.webm']:
        return 'video'
    elif ext in ['.pdf']:
        return 'pdf'
    else:
        return 'other'

def process_media_file(file_info, dry_run=False):
    """
    Process a single media file, linking it to messages if applicable.
    """
    path = file_info['path']
    file_id = file_info.get('file_id')
    if not file_id:
        logger.warning(f"No file ID found for {path}")
        return False
    
    media_type = get_media_type(path)
    
    with get_session() as session:
        # Check if the media entry already exists
        existing_media = session.query(Media).filter(
            Media.file_path == file_info['relative_path']
        ).first()
        
        if not existing_media:
            existing_media = session.query(Media).filter(
                Media.original_file_id == file_id
            ).first()
        
        if existing_media:
            logger.info(f"Media entry already exists for {file_id} ({existing_media.id})")
            
            # Update fields that might be missing
            if not existing_media.original_file_id:
                logger.info(f"Updating original_file_id for {existing_media.id}")
                if not dry_run:
                    existing_media.original_file_id = file_id
            
            if not existing_media.file_name:
                logger.info(f"Updating file_name for {existing_media.id}")
                if not dry_run:
                    existing_media.file_name = file_info['name']
            
            if not existing_media.is_generated and file_info['is_generated']:
                logger.info(f"Updating is_generated for {existing_media.id}")
                if not dry_run:
                    existing_media.is_generated = True
            
            media_id = existing_media.id
        else:
            # Create a new media entry
            if not dry_run:
                new_media = Media(
                    id=uuid.uuid4(),
                    file_path=file_info['relative_path'],
                    media_type=media_type,
                    original_file_id=file_id,
                    file_name=file_info['name'],
                    is_generated=file_info['is_generated']
                )
                session.add(new_media)
                session.flush()  # Get the ID
                media_id = new_media.id
                logger.info(f"Created new media entry: {media_id}")
            else:
                media_id = "(would create new entry)"
                logger.info(f"Would create new media entry for {file_info['name']}")
        
        # Find messages that reference this file ID
        referencing_messages = session.query(Message).filter(
            func.cast(Message.content, 'text').ilike(f"%{file_id}%")
        ).all()
        
        linked_count = 0
        for msg in referencing_messages:
            if msg.meta_info and 'author_role' in msg.meta_info:
                role = msg.meta_info.get('author_role', '').lower()
                
                # For user messages with attachments
                if role == 'user' and msg.meta_info.get('attachments'):
                    attachments = msg.meta_info.get('attachments', [])
                    for att in attachments:
                        if att.get('id') == file_id and existing_media:
                            if not dry_run:
                                # Since there's no message_id in the media table,
                                # we set the message's media_id to point to this media
                                msg.media_id = existing_media.id
                            logger.info(f"Linked user message {msg.id} to media {media_id}")
                            linked_count += 1
                
                # For assistant messages that generate images
                elif role == 'assistant' and file_info['is_generated'] and existing_media:
                    # We can't set linked_message_id directly,
                    # so we'll store this association in meta_info
                    if not dry_run and msg.meta_info:
                        if 'referenced_media' not in msg.meta_info:
                            msg.meta_info['referenced_media'] = []
                        
                        # Add this media to the referenced_media list if not already there
                        media_refs = msg.meta_info['referenced_media']
                        if not any(m.get('id') == str(existing_media.id) for m in media_refs):
                            media_refs.append({
                                'id': str(existing_media.id),
                                'file_id': file_id,
                                'file_path': existing_media.file_path
                            })
                    
                    logger.info(f"Linked assistant message {msg.id} to generated media {media_id} via meta_info")
                    linked_count += 1
        
        if not dry_run:
            session.commit()
        
        return linked_count > 0

def update_message_attachments(dry_run=False):
    """
    Update message meta_info to include references to media files.
    """
    with get_session() as session:
        # Get all messages with media_id set
        messages_with_media = session.query(Message).filter(
            Message.media_id.isnot(None)
        ).all()
        
        updated_count = 0
        for msg in messages_with_media:
            # Get the linked media
            media = session.query(Media).filter(Media.id == msg.media_id).first()
            if not media:
                continue
                
            # Update meta_info
            if not msg.meta_info:
                msg.meta_info = {}
            
            # Ensure attachments list exists
            if 'attachments' not in msg.meta_info:
                msg.meta_info['attachments'] = []
            
            # Add media info if not already present
            attachments = msg.meta_info['attachments']
            existing_ids = {att.get('id') for att in attachments if att.get('id')}
            
            if media.original_file_id and media.original_file_id not in existing_ids:
                if not dry_run:
                    attachments.append({
                        'id': media.original_file_id,
                        'name': media.file_name or '',
                        'media_id': str(media.id),
                        'media_type': media.media_type
                    })
                updated_count += 1
                logger.info(f"Updated message {msg.id} with attachment reference to media {media.id}")
            
            # Save changes
            if not dry_run:
                msg.meta_info['attachments'] = attachments
        
        if not dry_run:
            session.commit()
        
        return updated_count

def main():
    parser = argparse.ArgumentParser(description="Process media files and link them to messages")
    parser.add_argument('--chat-folder', default='chat', help='Path to the chat folder containing media files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of files to process (0 for all)')
    parser.add_argument('--update-messages', action='store_true', help='Also update message meta_info with media references')
    
    args = parser.parse_args()
    
    # Scan and process media files
    media_files = scan_media_files(args.chat_folder, args.limit)
    processed_count = 0
    linked_count = 0
    
    for file_info in media_files:
        processed_count += 1
        if processed_count % 100 == 0:
            logger.info(f"Processed {processed_count}/{len(media_files)} files...")
        
        if process_media_file(file_info, args.dry_run):
            linked_count += 1
    
    logger.info(f"Processed {processed_count} media files, linked {linked_count} to messages")
    
    # Update message attachments if requested
    if args.update_messages:
        updated = update_message_attachments(args.dry_run)
        logger.info(f"Updated {updated} message attachment references")
    
    if args.dry_run:
        logger.info("This was a dry run. No changes were made to the database.")

if __name__ == "__main__":
    main()