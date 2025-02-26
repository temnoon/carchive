#!/usr/bin/env python3
# scripts/process_media_direct.py

"""
Process media files to link them with messages using direct SQL.
This avoids SQLAlchemy schema validation issues.
"""

import os
import re
import uuid
from pathlib import Path
import logging
import sys
import argparse
import psycopg2
import psycopg2.extras
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from carchive.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get a connection to the database."""
    conn = psycopg2.connect(
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.get_secure_value("DB_PASS"),
        host=settings.db_host
    )
    return conn

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

def process_media_file(conn, file_info, dry_run=False):
    """
    Process a single media file, linking it to messages if applicable.
    """
    path = file_info['path']
    file_id = file_info.get('file_id')
    if not file_id:
        logger.warning(f"No file ID found for {path}")
        return False
    
    media_type = get_media_type(path)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    try:
        # Check if the media entry already exists
        cursor.execute(
            "SELECT * FROM media WHERE file_path = %s OR original_file_id = %s", 
            (file_info['relative_path'], file_id)
        )
        existing_media = cursor.fetchone()
        
        if existing_media:
            logger.info(f"Media entry already exists for {file_id} ({existing_media['id']})")
            
            # Update fields that might be missing
            if not existing_media['original_file_id']:
                logger.info(f"Updating original_file_id for {existing_media['id']}")
                if not dry_run:
                    cursor.execute(
                        "UPDATE media SET original_file_id = %s WHERE id = %s",
                        (file_id, existing_media['id'])
                    )
            
            if not existing_media['file_name']:
                logger.info(f"Updating file_name for {existing_media['id']}")
                if not dry_run:
                    cursor.execute(
                        "UPDATE media SET file_name = %s WHERE id = %s",
                        (file_info['name'], existing_media['id'])
                    )
            
            if not existing_media['is_generated'] and file_info['is_generated']:
                logger.info(f"Updating is_generated for {existing_media['id']}")
                if not dry_run:
                    cursor.execute(
                        "UPDATE media SET is_generated = TRUE WHERE id = %s",
                        (existing_media['id'],)
                    )
            
            media_id = existing_media['id']
        else:
            # Create a new media entry
            if not dry_run:
                new_id = uuid.uuid4()
                cursor.execute(
                    """
                    INSERT INTO media (id, file_path, media_type, original_file_id, file_name, is_generated)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (new_id, file_info['relative_path'], media_type, file_id, file_info['name'], file_info['is_generated'])
                )
                media_id = new_id
                logger.info(f"Created new media entry: {media_id}")
            else:
                media_id = "(would create new entry)"
                logger.info(f"Would create new media entry for {file_info['name']}")
        
        # Find messages that reference this file ID using a LIKE query
        cursor.execute(
            "SELECT id, content, meta_info FROM messages WHERE content LIKE %s",
            (f'%{file_id}%',)
        )
        referencing_messages = cursor.fetchall()
        
        linked_count = 0
        for msg in referencing_messages:
            meta_info = msg['meta_info'] if msg['meta_info'] else {}
            
            if 'author_role' in meta_info:
                role = meta_info.get('author_role', '').lower()
                
                # For user messages with attachments
                if role == 'user' and meta_info.get('attachments'):
                    attachments = meta_info.get('attachments', [])
                    for att in attachments:
                        if att.get('id') == file_id and not dry_run and existing_media:
                            # Set the message's media_id to this media
                            cursor.execute(
                                "UPDATE messages SET media_id = %s WHERE id = %s",
                                (existing_media['id'], msg['id'])
                            )
                            logger.info(f"Linked user message {msg['id']} to media {media_id}")
                            linked_count += 1
                
                # For assistant messages that generate images
                elif role == 'assistant' and file_info['is_generated'] and not dry_run and existing_media:
                    # Store association in meta_info
                    if 'referenced_media' not in meta_info:
                        meta_info['referenced_media'] = []
                    
                    # Add this media to the referenced_media list if not already there
                    media_refs = meta_info['referenced_media']
                    if not any(m.get('id') == str(existing_media['id']) for m in media_refs):
                        media_refs.append({
                            'id': str(existing_media['id']),
                            'file_id': file_id,
                            'file_path': existing_media['file_path']
                        })
                        
                        # Update the message's meta_info
                        cursor.execute(
                            "UPDATE messages SET meta_info = %s WHERE id = %s",
                            (json.dumps(meta_info), msg['id'])
                        )
                    
                    logger.info(f"Linked assistant message {msg['id']} to generated media {media_id} via meta_info")
                    linked_count += 1
        
        if not dry_run:
            conn.commit()
        
        return linked_count > 0
    
    except Exception as e:
        logger.error(f"Error processing file {path}: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()

def update_message_attachments(conn, dry_run=False):
    """
    Update message meta_info to include references to media files.
    """
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        # Get all messages with media_id set
        cursor.execute("SELECT id, meta_info, media_id FROM messages WHERE media_id IS NOT NULL")
        messages_with_media = cursor.fetchall()
        
        updated_count = 0
        for msg in messages_with_media:
            if not msg['media_id']:
                continue
                
            # Get the linked media
            cursor.execute("SELECT * FROM media WHERE id = %s", (msg['media_id'],))
            media = cursor.fetchone()
            if not media:
                continue
                
            # Update meta_info
            meta_info = msg['meta_info'] if msg['meta_info'] else {}
            
            # Ensure attachments list exists
            if 'attachments' not in meta_info:
                meta_info['attachments'] = []
            
            # Add media info if not already present
            attachments = meta_info['attachments']
            existing_ids = {att.get('id') for att in attachments if att.get('id')}
            
            if media['original_file_id'] and media['original_file_id'] not in existing_ids:
                if not dry_run:
                    attachments.append({
                        'id': media['original_file_id'],
                        'name': media['file_name'] or '',
                        'media_id': str(media['id']),
                        'media_type': media['media_type']
                    })
                    
                    # Update the message's meta_info
                    cursor.execute(
                        "UPDATE messages SET meta_info = %s WHERE id = %s",
                        (json.dumps(meta_info), msg['id'])
                    )
                
                updated_count += 1
                logger.info(f"Updated message {msg['id']} with attachment reference to media {media['id']}")
        
        if not dry_run:
            conn.commit()
        
        return updated_count
    
    except Exception as e:
        logger.error(f"Error updating message attachments: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()

def main():
    parser = argparse.ArgumentParser(description="Process media files and link them to messages")
    parser.add_argument('--chat-folder', default='chat', help='Path to the chat folder containing media files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--limit', type=int, default=0, help='Limit the number of files to process (0 for all)')
    parser.add_argument('--update-messages', action='store_true', help='Also update message meta_info with media references')
    
    args = parser.parse_args()
    
    # Connect to the database
    conn = get_db_connection()
    
    try:
        # Scan and process media files
        media_files = scan_media_files(args.chat_folder, args.limit)
        processed_count = 0
        linked_count = 0
        
        for file_info in media_files:
            processed_count += 1
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count}/{len(media_files)} files...")
            
            if process_media_file(conn, file_info, args.dry_run):
                linked_count += 1
        
        logger.info(f"Processed {processed_count} media files, linked {linked_count} to messages")
        
        # Update message attachments if requested
        if args.update_messages:
            updated = update_message_attachments(conn, args.dry_run)
            logger.info(f"Updated {updated} message attachment references")
        
        if args.dry_run:
            logger.info("This was a dry run. No changes were made to the database.")
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()