#!/usr/bin/env python
"""
This script imports media files from the chat3 archive and links them to messages.
"""

import os
import sys
import re
import uuid
import hashlib
import logging
import argparse
from datetime import datetime
from sqlalchemy import text
from carchive.database.session import get_session
from carchive.database.models import Media, Message, MessageMedia

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"chat3_media_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("chat3_media_import")

# Constants
CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"
CHAT3_DIR = "chat3"

def calculate_checksum(file_path):
    """Calculate MD5 checksum for a file."""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate checksum for {file_path}: {e}")
        return None

def guess_mime_type(file_path):
    """Guess MIME type based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
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
    return ext_to_mime.get(ext, 'application/octet-stream')

def determine_media_type(file_path):
    """Determine media type based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
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

def import_media_files(source_dir, target_dir, dry_run=True, batch_size=100):
    """
    Import media files from chat3 archive and link them to messages.
    
    Args:
        source_dir: Path to chat3 directory containing media files
        target_dir: Base directory for the new media structure
        dry_run: If True, don't actually copy files or update DB
        batch_size: Number of files to process in each database batch
        
    Returns:
        Dictionary with import statistics
    """
    # Pattern for extracting file IDs
    file_dash_pattern = re.compile(r"^file-([^-]+)-(.+)$")
    
    # Create target directory structure
    target_chatgpt_dir = os.path.join(target_dir, "chatgpt")
    target_chat3_dir = os.path.join(target_chatgpt_dir, CHAT3_DIR)
    os.makedirs(target_chat3_dir, exist_ok=True)
    
    # Stats for reporting
    stats = {
        "total_files": 0,
        "processed": 0,
        "imported": 0,
        "skipped": 0,
        "linked_messages": 0,
        "errors": 0
    }
    
    # Get all media files from source directory
    media_files = []
    for root, _, files in os.walk(source_dir):
        for filename in files:
            if not filename.startswith('.'):  # Skip hidden files
                file_path = os.path.join(root, filename)
                stats["total_files"] += 1
                media_files.append(file_path)
    
    logger.info(f"Found {stats['total_files']} media files in {source_dir}")
    
    # Process files in batches
    current_batch = []
    
    with get_session() as session:
        for file_path in media_files:
            try:
                stats["processed"] += 1
                if stats["processed"] % 100 == 0:
                    logger.info(f"Processed {stats['processed']}/{stats['total_files']} files...")
                
                filename = os.path.basename(file_path)
                match = file_dash_pattern.match(filename)
                
                if not match:
                    logger.warning(f"Filename does not match expected pattern: {filename}")
                    stats["skipped"] += 1
                    continue
                
                file_id = match.group(1)
                original_name = match.group(2)
                full_file_id = f"file-{file_id}"
                
                # Determine target path in new structure
                target_path = os.path.join(target_chat3_dir, filename)
                relative_path = os.path.join("chatgpt", CHAT3_DIR, filename)
                
                # Calculate checksum, file size, and determine media type
                checksum = calculate_checksum(file_path)
                file_size = os.path.getsize(file_path)
                media_type = determine_media_type(file_path)
                mime_type = guess_mime_type(file_path)
                
                # Is this a DALL-E generation?
                is_generated = 'dalle-generations' in file_path
                
                # Create media database record
                media_id = uuid.uuid4()
                media_record = Media(
                    id=media_id,
                    file_path=target_path,
                    media_type=media_type,
                    mime_type=mime_type,
                    file_size=file_size,
                    original_file_name=original_name,
                    original_file_id=full_file_id,
                    is_generated=is_generated,
                    checksum=checksum,
                    provider_id=CHATGPT_PROVIDER_ID,
                    archive_source=CHAT3_DIR,
                    relative_path=relative_path,
                    original_path=file_path
                )
                
                if not dry_run:
                    # Copy file to new location if it doesn't exist
                    if not os.path.exists(target_path):
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        import shutil
                        shutil.copy2(file_path, target_path)
                        logger.debug(f"Copied {file_path} to {target_path}")
                    
                    # Add media record to batch
                    session.add(media_record)
                    current_batch.append(media_record)
                
                stats["imported"] += 1
                
                # Find messages that reference this file ID
                if not dry_run:
                    # Use the ID with the file- prefix to search in messages
                    referencing_messages = session.query(Message).filter(
                        Message.content.ilike(f"%{full_file_id}%")
                    ).all()
                    
                    # For each message that references this file, create a link
                    for msg in referencing_messages:
                        if msg.meta_info and 'author_role' in msg.meta_info:
                            role = msg.meta_info.get('author_role', '').lower()
                            
                            # For user messages with attachments
                            if role == 'user' and msg.meta_info.get('attachments'):
                                attachments = msg.meta_info.get('attachments', [])
                                for att in attachments:
                                    att_id = att.get('id')
                                    # Match either full ID or just the part after file-
                                    if att_id == file_id or att_id == full_file_id:
                                        # Create MessageMedia association
                                        message_media = MessageMedia(
                                            id=uuid.uuid4(),
                                            message_id=msg.id,
                                            media_id=media_id,
                                            association_type="uploaded"
                                        )
                                        session.add(message_media)
                                        stats["linked_messages"] += 1
                                        logger.debug(f"Linked user message {msg.id} to media {media_id}")
                            
                            # For assistant messages that generate images
                            elif role == 'assistant' and is_generated:
                                # Create MessageMedia association
                                message_media = MessageMedia(
                                    id=uuid.uuid4(),
                                    message_id=msg.id,
                                    media_id=media_id,
                                    association_type="generated"
                                )
                                session.add(message_media)
                                stats["linked_messages"] += 1
                                logger.debug(f"Linked assistant message {msg.id} to generated media {media_id}")
                
                # Commit every batch_size records
                if len(current_batch) >= batch_size and not dry_run:
                    session.commit()
                    logger.info(f"Committed batch of {len(current_batch)} records")
                    current_batch = []
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}")
                stats["errors"] += 1
        
        # Commit any remaining records
        if current_batch and not dry_run:
            try:
                session.commit()
                logger.info(f"Committed final batch of {len(current_batch)} records")
            except Exception as e:
                logger.error(f"Error committing final batch: {e}")
                session.rollback()
                stats["errors"] += len(current_batch)
    
    return stats

def main():
    parser = argparse.ArgumentParser(description="Import media files from chat3 archive")
    parser.add_argument("--source-dir", default="chat3", help="Path to chat3 directory")
    parser.add_argument("--target-dir", default="media_new", help="Target directory for new media structure")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually copy files or update database")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of records to process in each batch")
    args = parser.parse_args()
    
    # Validate source directory
    if not os.path.isdir(args.source_dir):
        logger.error(f"Source directory does not exist: {args.source_dir}")
        return 1
    
    # Start import
    start_time = datetime.now()
    logger.info(f"Starting chat3 media import at {start_time}")
    logger.info(f"Source directory: {args.source_dir}")
    logger.info(f"Target directory: {args.target_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        stats = import_media_files(
            source_dir=args.source_dir,
            target_dir=args.target_dir,
            dry_run=args.dry_run,
            batch_size=args.batch_size
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Import completed in {duration}")
        logger.info(f"Total files found: {stats['total_files']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Imported: {stats['imported']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Messages linked: {stats['linked_messages']}")
        logger.info(f"Errors: {stats['errors']}")
        
        if args.dry_run:
            logger.info("\nThis was a dry run. Run without --dry-run to apply changes.")
        
        return 0
    
    except Exception as e:
        logger.error(f"Import failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())