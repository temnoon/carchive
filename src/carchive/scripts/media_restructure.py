#!/usr/bin/env python
"""
Media restructuring script for carchive.

This script implements the new media directory structure:
- media_new/
  ├── chatgpt/
  │   ├── chat/
  │   ├── chat2/
  │   └── chat3/
  └── shared/

It preserves original filenames and updates the database records accordingly.
"""

import os
import sys
import uuid
import shutil
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Set
import json
import argparse
from pathlib import Path
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Media

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"media_restructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("media_restructure")

# Constants
CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"
CLAUDE_PROVIDER_ID = "22222222-2222-2222-2222-222222222222"
PERPLEXITY_PROVIDER_ID = "33333333-3333-3333-3333-333333333333"

# Source directories
CHAT_DIR = "chat"
CHAT2_DIR = "chat2"
CHAT3_DIR = "chat3"

# Archive priorities (highest to lowest)
ARCHIVE_PRIORITY = [CHAT3_DIR, CHAT2_DIR, CHAT_DIR]


def calculate_checksum(file_path: str) -> Optional[str]:
    """Calculate MD5 checksum for a file."""
    try:
        with open(file_path, "rb") as f:
            file_hash = hashlib.md5()
            chunk = f.read(8192)
            while chunk:
                file_hash.update(chunk)
                chunk = f.read(8192)
        return file_hash.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate checksum for {file_path}: {e}")
        return None


def find_file_in_sources(file_id: str, sources: List[str]) -> Optional[Dict]:
    """
    Search for a file with the given ID across multiple source directories.
    Returns details of the first match found according to source priority.
    """
    for source in sources:
        if not os.path.isdir(source):
            logger.warning(f"Source directory does not exist: {source}")
            continue
            
        for filename in os.listdir(source):
            # Match ChatGPT archive file pattern "file-{ID}-{filename}"
            if filename.startswith("file-") and file_id in filename:
                file_path = os.path.join(source, filename)
                # Extract original filename (after the ID part)
                parts = filename.split('-', 2)
                original_name = parts[2] if len(parts) > 2 else filename
                
                return {
                    "path": file_path,
                    "source": os.path.basename(source),
                    "filename": filename,
                    "original_name": original_name
                }
    
    # If nothing found with full ID, try partial matching with first 8 chars
    short_id = file_id[:8]
    for source in sources:
        if not os.path.isdir(source):
            continue
            
        for filename in os.listdir(source):
            if filename.startswith("file-") and short_id in filename:
                file_path = os.path.join(source, filename)
                parts = filename.split('-', 2)
                original_name = parts[2] if len(parts) > 2 else filename
                
                return {
                    "path": file_path,
                    "source": os.path.basename(source),
                    "filename": filename,
                    "original_name": original_name
                }
    
    return None


def setup_directory_structure(base_dir: str) -> Dict[str, str]:
    """
    Create the new directory structure for media files.
    Returns a dictionary of path mappings.
    """
    paths = {
        "base": base_dir,
        "chatgpt": os.path.join(base_dir, "chatgpt"),
        "chat": os.path.join(base_dir, "chatgpt", CHAT_DIR),
        "chat2": os.path.join(base_dir, "chatgpt", CHAT2_DIR),
        "chat3": os.path.join(base_dir, "chatgpt", CHAT3_DIR),
        "shared": os.path.join(base_dir, "shared"),
    }
    
    # Create directories
    for path in paths.values():
        os.makedirs(path, exist_ok=True)
        logger.info(f"Ensured directory exists: {path}")
    
    return paths


def get_target_path(file_details: Dict, paths: Dict[str, str]) -> str:
    """
    Determine the target path for a file based on its source.
    Uses the original archive structure but with preserved filenames.
    """
    source = file_details.get("source")
    filename = file_details.get("filename")
    
    if source in [CHAT_DIR, CHAT2_DIR, CHAT3_DIR]:
        return os.path.join(paths["chatgpt"], source, filename)
    else:
        # Default to shared directory if source is unknown
        return os.path.join(paths["shared"], filename)


def migrate_media_files(
    session: Session, 
    source_dirs: List[str], 
    target_base_dir: str,
    dry_run: bool = False,
    batch_size: int = 100
) -> Dict:
    """
    Migrate media files to the new structure and update database records.
    
    Args:
        session: Database session
        source_dirs: List of source directories to search
        target_base_dir: Base directory for the new structure
        dry_run: If True, don't actually copy files or update DB
        batch_size: Number of records to process in each batch
        
    Returns:
        Dictionary with migration statistics
    """
    # Setup target directory structure
    paths = setup_directory_structure(target_base_dir)
    
    # Statistics
    stats = {
        "total": 0,
        "migrated": 0,
        "skipped": 0,
        "not_found": 0,
        "errors": 0
    }
    
    # Process media records in batches
    offset = 0
    while True:
        # Get a batch of media records
        media_batch = session.query(Media).order_by(Media.id).offset(offset).limit(batch_size).all()
        
        if not media_batch:
            break  # No more records
            
        offset += len(media_batch)
        stats["total"] += len(media_batch)
        
        if stats["total"] % 500 == 0:
            logger.info(f"Processed {stats['total']} media records so far...")
        
        # Process each media record
        for media in media_batch:
            try:
                # Skip if we've already migrated this record
                if media.archive_source and media.relative_path:
                    logger.debug(f"Media already migrated: {media.id}")
                    stats["skipped"] += 1
                    continue
                
                # Find the file in source directories
                file_id = media.original_file_id
                if not file_id:
                    logger.warning(f"No original_file_id for media: {media.id}")
                    stats["not_found"] += 1
                    continue
                
                file_details = find_file_in_sources(file_id, source_dirs)
                if not file_details:
                    logger.warning(f"File not found for media ID: {media.id}, original file ID: {file_id}")
                    stats["not_found"] += 1
                    continue
                
                # Determine target path
                target_path = get_target_path(file_details, paths)
                relative_path = os.path.relpath(target_path, target_base_dir)
                
                # In dry run mode, just log what would be done
                if dry_run:
                    logger.info(f"Would copy {file_details['path']} to {target_path}")
                    logger.info(f"Would update media {media.id} with archive_source={file_details['source']}, " 
                                f"relative_path={relative_path}, original_path={file_details['path']}")
                    stats["migrated"] += 1
                    continue
                
                # Copy the file if not already there
                if not os.path.exists(target_path):
                    try:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        shutil.copy2(file_details["path"], target_path)
                        logger.debug(f"Copied {file_details['path']} to {target_path}")
                    except Exception as e:
                        logger.error(f"Failed to copy file {file_details['path']}: {e}")
                        stats["errors"] += 1
                        continue
                
                # Update the database record
                media.archive_source = file_details["source"]
                media.relative_path = relative_path
                media.original_path = file_details["path"]
                media.file_path = target_path
                
                stats["migrated"] += 1
                
            except Exception as e:
                logger.error(f"Error processing media {media.id}: {e}")
                stats["errors"] += 1
        
        # Commit each batch if not in dry run mode
        if not dry_run:
            session.commit()
            logger.info(f"Committed batch of {len(media_batch)} records")
    
    return stats


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Migrate media files to the new structure')
    parser.add_argument('--source-dirs', nargs='+', required=True, 
                        help='Source directories to search for files')
    parser.add_argument('--target-dir', required=True, 
                        help='Target base directory for the new structure')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Do not actually copy files or update database')
    parser.add_argument('--batch-size', type=int, default=100, 
                        help='Number of records to process in each batch')
    
    args = parser.parse_args()
    
    # Validate source directories
    valid_sources = []
    for source in args.source_dirs:
        if os.path.isdir(source):
            valid_sources.append(source)
        else:
            logger.warning(f"Source directory does not exist and will be skipped: {source}")
    
    if not valid_sources:
        logger.error("No valid source directories provided")
        return 1
    
    # Start migration
    start_time = datetime.now()
    logger.info(f"Starting media restructuring at {start_time}")
    logger.info(f"Source directories: {valid_sources}")
    logger.info(f"Target directory: {args.target_dir}")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        with get_session() as session:
            stats = migrate_media_files(
                session=session,
                source_dirs=valid_sources,
                target_base_dir=args.target_dir,
                dry_run=args.dry_run,
                batch_size=args.batch_size
            )
            
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info(f"Migration completed in {duration}")
        logger.info(f"Total records: {stats['total']}")
        logger.info(f"Migrated: {stats['migrated']}")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Not found: {stats['not_found']}")
        logger.info(f"Errors: {stats['errors']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())