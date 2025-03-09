#!/usr/bin/env python3
"""
Fix original_file_id values in the media table to properly link to DALL-E generated images.

This script:
1. Scans the dalle-generations directory to extract file IDs
2. Updates corresponding media records in the database
3. Ensures media records have both the full ID and proper associations

Usage:
    python scripts/fix_dalle/fix_original_file_ids.py

"""
import os
import re
import uuid
from pathlib import Path
import hashlib
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, or_, func, update
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Media, Message, MessageMedia, Provider

# CHATGPT Provider ID
CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"

def scan_dalle_directory() -> Dict[str, Path]:
    """
    Scan the dalle-generations directory and return a mapping of file IDs to paths.
    """
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


def calculate_file_checksum(file_path: Path) -> str:
    """Calculate MD5 checksum for a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def find_media_by_checksum(session: Session, checksum: str) -> Optional[Media]:
    """Find a media record by its checksum."""
    return session.query(Media).filter(Media.checksum == checksum).first()


def find_media_by_filename(session: Session, filename: str) -> Optional[Media]:
    """Find a media record by the filename in its file_path."""
    # Extract UUID part from filename
    uuid_match = re.search(r"-([^-]+)\.webp$", filename)
    if uuid_match:
        uuid_part = uuid_match.group(1)
        return session.query(Media).filter(
            Media.file_path.like(f"%{uuid_part}.webp")
        ).first()
    return None


def update_media_record(session: Session, media_id: uuid.UUID, file_id: str, is_dalle: bool = True) -> None:
    """Update a media record with the correct original_file_id and is_generated flag."""
    media = session.query(Media).filter(Media.id == media_id).first()
    if not media:
        return
    
    # Only update if needed
    if (media.original_file_id != file_id) or (not media.is_generated and is_dalle):
        # Preserve existing original_file_id if it's not null or empty
        if not media.original_file_id or file_id not in media.original_file_id:
            # If current value exists, append the new ID
            if media.original_file_id:
                # Make full file-id format
                full_file_id = f"file-{file_id}" if not file_id.startswith("file-") else file_id
                media.original_file_id = full_file_id
            else:
                # Set new value
                full_file_id = f"file-{file_id}" if not file_id.startswith("file-") else file_id
                media.original_file_id = full_file_id
        
        # Always set is_generated for DALL-E images
        if is_dalle and not media.is_generated:
            media.is_generated = True
            
        session.commit()
        print(f"Updated media record {media.id}: original_file_id='{media.original_file_id}', is_generated={media.is_generated}")


def find_message_references(session: Session, file_id: str) -> List[Message]:
    """Find messages that reference a specific file ID."""
    # Look for both 'file-{id}' and just '{id}'
    full_id = f"file-{file_id}" if not file_id.startswith("file-") else file_id
    bare_id = full_id.replace("file-", "")
    
    return session.query(Message).filter(
        or_(
            Message.content.like(f"%{full_id}%"),
            Message.content.like(f"%{bare_id}%"),
            Message.content.like(f"%[Asset: {full_id}]%")
        )
    ).all()


def create_message_media_association(session: Session, message_id: uuid.UUID, media_id: uuid.UUID) -> None:
    """Create a message-media association if it doesn't exist."""
    # Check if association already exists
    existing = session.query(MessageMedia).filter(
        and_(
            MessageMedia.message_id == message_id,
            MessageMedia.media_id == media_id
        )
    ).first()
    
    if existing:
        # Update association type if it's not already 'generated'
        if existing.association_type != 'generated':
            existing.association_type = 'generated'
            session.commit()
            print(f"Updated association type for message {message_id} and media {media_id}")
        return
    
    # Create new association
    new_assoc = MessageMedia(
        id=uuid.uuid4(),
        message_id=message_id,
        media_id=media_id,
        association_type='generated'
    )
    session.add(new_assoc)
    session.commit()
    print(f"Created new association between message {message_id} and media {media_id}")


def main():
    """Main function to fix original_file_id values."""
    # 1. Scan dalle-generations directory
    dalle_files = scan_dalle_directory()
    if not dalle_files:
        print("No DALL-E images found. Exiting.")
        return
    
    with get_session() as session:
        # Process each DALL-E file
        for file_id, file_path in dalle_files.items():
            print(f"\nProcessing DALL-E file: {file_path.name}")
            print(f"File ID: {file_id}")
            
            # Calculate checksum
            checksum = calculate_file_checksum(file_path)
            
            # Try to find matching media record by checksum
            media = find_media_by_checksum(session, checksum)
            
            # If not found by checksum, try by filename
            if not media:
                media = find_media_by_filename(session, file_path.name)
            
            if media:
                print(f"Found matching media record: {media.id}")
                print(f"  Current original_file_id: {media.original_file_id}")
                print(f"  Current is_generated: {media.is_generated}")
                
                # Update the media record with the correct file ID
                update_media_record(session, media.id, file_id)
                
                # Find messages that reference this file ID
                messages = find_message_references(session, file_id)
                print(f"Found {len(messages)} messages referencing this file ID")
                
                # Create message-media associations
                for message in messages:
                    create_message_media_association(session, message.id, media.id)
            else:
                print(f"No matching media record found for {file_path.name}")
        
        # Now find media records with is_generated=True but no original_file_id
        missing_id_media = session.query(Media).filter(
            and_(
                Media.is_generated == True,
                or_(
                    Media.original_file_id == None,
                    Media.original_file_id == ""
                )
            )
        ).all()
        
        print(f"\nFound {len(missing_id_media)} generated media records with missing original_file_id")
        
        # For these, we'll set a placeholder ID
        for media in missing_id_media:
            placeholder_id = f"file-generated-{str(uuid.uuid4())[:8]}"
            print(f"Setting placeholder ID {placeholder_id} for media {media.id}")
            media.original_file_id = placeholder_id
            session.commit()
        
        print("\nFile ID fix process completed!")


if __name__ == "__main__":
    main()