#!/usr/bin/env python3
"""
Script to update file paths in media records for DALL-E images.

This script:
1. Identifies DALL-E images that have .webp extension
2. Fixes their file paths to point to the correct location in media/chatgpt
3. Ensures database records are consistent with the actual file locations

Usage:
    python scripts/fix_dalle/update_media_paths.py

"""
import os
import re
import uuid
from pathlib import Path
import hashlib
import shutil
from typing import List, Dict, Tuple, Optional
import json

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Media, Message, MessageMedia, Provider


# CHATGPT Provider ID
CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"


def scan_media_directory() -> Dict[str, Path]:
    """Scan the media/chatgpt directory and return a map of filename -> path."""
    media_dir = Path("media/chatgpt")
    if not media_dir.exists():
        print(f"Directory {media_dir} does not exist!")
        return {}
    
    # Create a dictionary mapping filenames to their paths
    media_files = {}
    for file in media_dir.glob("*.webp"):
        media_files[file.name] = file
    
    print(f"Found {len(media_files)} .webp files in {media_dir}")
    return media_files


def scan_dalle_directory() -> Dict[str, Path]:
    """Scan the chat2/dalle-generations directory and return a map of file ID -> path."""
    dalle_dir = Path("chat2/dalle-generations")
    if not dalle_dir.exists():
        print(f"Directory {dalle_dir} does not exist!")
        return {}
    
    # Create a dictionary mapping file IDs to their paths
    dalle_files = {}
    for file in dalle_dir.glob("*.webp"):
        file_id = extract_file_id(file.name)
        if file_id:
            dalle_files[file_id] = file
    
    print(f"Found {len(dalle_files)} DALL-E generated images in {dalle_dir}")
    return dalle_files


def extract_file_id(filename: str) -> Optional[str]:
    """Extract the file ID from a DALL-E generated image filename."""
    # For DALL-E generated files (e.g., file-ABC123-uuid.webp)
    pattern = re.compile(r"^file-([^-]+)-")
    match = pattern.match(filename)
    if match:
        return match.group(1)
    return None


def extract_uuid_from_filename(filename: str) -> Optional[str]:
    """Extract the UUID part from a DALL-E generated image filename."""
    # For DALL-E generated files (e.g., file-ABC123-uuid.webp)
    pattern = re.compile(r"^file-[^-]+-([^.]+)\.webp$")
    match = pattern.match(filename)
    if match:
        return match.group(1)
    return None


def calculate_file_checksum(file_path: str) -> str:
    """Calculate MD5 checksum for a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def find_media_by_original_id(session: Session, original_file_id: str) -> Optional[Media]:
    """Find a media record by its original_file_id."""
    return session.query(Media).filter(
        Media.original_file_id == original_file_id
    ).first()


def find_media_by_path(session: Session, file_path: str) -> Optional[Media]:
    """Find a media record by its file_path."""
    return session.query(Media).filter(
        Media.file_path == file_path
    ).first()


def update_media_record(session: Session, media: Media, new_path: str) -> None:
    """Update a media record with a new file path and mark as generated."""
    old_path = media.file_path
    media.file_path = new_path
    media.is_generated = True
    session.commit()
    print(f"Updated media record {media.id}: path={old_path} -> {new_path}, is_generated=True")


def ensure_file_exists(source_path: Path, target_path: Path) -> bool:
    """Ensure a file exists at the target path, copying if necessary."""
    if target_path.exists():
        return True
    
    if not source_path.exists():
        print(f"Source file {source_path} does not exist!")
        return False
    
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        print(f"Copied {source_path} to {target_path}")
        return True
    except Exception as e:
        print(f"Error copying {source_path} to {target_path}: {e}")
        return False


def main():
    """Main function to update file paths for DALL-E generated images."""
    # 1. Scan directories
    media_files = scan_media_directory()
    dalle_files = scan_dalle_directory()
    
    if not dalle_files:
        print("No DALL-E images found. Exiting.")
        return
    
    # 2. Process each DALL-E image
    with get_session() as session:
        # Get ChatGPT provider
        chatgpt_provider = session.query(Provider).filter_by(id=CHATGPT_PROVIDER_ID).first()
        if not chatgpt_provider:
            print(f"ChatGPT provider not found with ID {CHATGPT_PROVIDER_ID}")
            return
        
        # Get all media records with .webp extension
        webp_media = session.query(Media).filter(
            and_(
                Media.provider_id == CHATGPT_PROVIDER_ID,
                Media.file_path.like("%.webp")
            )
        ).all()
        
        print(f"Found {len(webp_media)} .webp media records in the database")
        
        # Track which DALL-E files we've processed
        processed_dalle_files = set()
        
        # First, try to match media records to dalle files by original_file_id
        for file_id, dalle_path in dalle_files.items():
            # Find media record with matching original_file_id
            media = find_media_by_original_id(session, file_id)
            
            if media:
                # Get UUID part from filename
                uuid_part = extract_uuid_from_filename(dalle_path.name)
                if not uuid_part:
                    uuid_part = str(uuid.uuid4())
                
                # Determine target path in media/chatgpt
                target_filename = f"{uuid_part}.webp"
                target_path = Path("media/chatgpt") / target_filename
                
                # Ensure file exists at target path
                if ensure_file_exists(dalle_path, target_path):
                    # Update media record
                    update_media_record(session, media, str(target_path))
                    processed_dalle_files.add(file_id)
        
        # For unprocessed DALL-E files, create new media records
        for file_id, dalle_path in dalle_files.items():
            if file_id in processed_dalle_files:
                continue
            
            # Get UUID part from filename
            uuid_part = extract_uuid_from_filename(dalle_path.name)
            if not uuid_part:
                uuid_part = str(uuid.uuid4())
            
            # Determine target path in media/chatgpt
            target_filename = f"{uuid_part}.webp"
            target_path = Path("media/chatgpt") / target_filename
            
            # Check if target already exists in media records
            existing_media = find_media_by_path(session, str(target_path))
            
            if existing_media:
                # Update existing record
                if not existing_media.is_generated:
                    existing_media.is_generated = True
                    session.commit()
                    print(f"Updated existing media record {existing_media.id} (is_generated = True)")
                processed_dalle_files.add(file_id)
                continue
            
            # Ensure file exists at target path
            if ensure_file_exists(dalle_path, target_path):
                # Create new media record
                new_media = Media(
                    id=uuid.uuid4(),
                    file_path=str(target_path),
                    media_type="image",
                    provider_id=CHATGPT_PROVIDER_ID,
                    original_file_name=dalle_path.name,
                    original_file_id=file_id,
                    mime_type="image/webp",
                    file_size=os.path.getsize(dalle_path),
                    checksum=calculate_file_checksum(dalle_path),
                    is_generated=True,
                    source_url=None,
                    meta_info={"source": "DALL-E"}
                )
                session.add(new_media)
                session.commit()
                print(f"Created new media record {new_media.id} for DALL-E image {dalle_path.name}")
                processed_dalle_files.add(file_id)
        
        print(f"Processed {len(processed_dalle_files)} out of {len(dalle_files)} DALL-E files")
        print("Media path update completed!")


if __name__ == "__main__":
    main()