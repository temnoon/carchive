#!/usr/bin/env python3
"""
Script to find DALL-E generated images and update their database records.

This script:
1. Scans the chat2/dalle-generations directory for DALL-E generated images
2. Updates the corresponding media records in the database:
   - Sets is_generated = True for these images
   - Updates association_type to 'generated' in message_media
3. Associates images with tool messages containing 'DALL-E' text

Usage:
    python scripts/fix_dalle/find_dalle_images.py

"""
import os
import re
import uuid
from pathlib import Path
import hashlib
from typing import List, Dict, Tuple, Optional
import json

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Media, Message, MessageMedia, Provider


# CHATGPT Provider ID
CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"

def find_dalle_images() -> List[Path]:
    """Find all DALL-E generated images in the chat2/dalle-generations directory."""
    dalle_dir = Path("chat2/dalle-generations")
    if not dalle_dir.exists():
        print(f"Directory {dalle_dir} does not exist!")
        return []
    
    images = list(dalle_dir.glob("*.webp"))
    print(f"Found {len(images)} DALL-E generated images in {dalle_dir}")
    return images


def extract_file_id(filename: str) -> Optional[str]:
    """Extract the file ID from a DALL-E generated image filename."""
    # For DALL-E generated files (e.g., file-ABC123-uuid.webp)
    pattern = re.compile(r"^file-([^-]+)-")
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


def find_media_record(session: Session, original_file_id: str) -> Optional[Media]:
    """Find an existing media record by original_file_id."""
    return session.query(Media).filter(
        Media.original_file_id.ilike(f"%{original_file_id}%")
    ).first()


def find_dall_e_tool_messages(session: Session) -> List[Message]:
    """Find tool messages containing DALL-E references."""
    return session.query(Message).filter(
        and_(
            Message.role == 'tool',
            or_(
                Message.content.ilike('%DALL-E%'),
                Message.content.ilike('%DALLE%'),
                Message.content.ilike('%dalle%')
            )
        )
    ).all()


def find_existing_media_messages(session: Session, media_id: uuid.UUID) -> List[MessageMedia]:
    """Find existing message-media associations for a media item."""
    return session.query(MessageMedia).filter(
        MessageMedia.media_id == media_id
    ).all()


def update_media_record(session: Session, media: Media) -> None:
    """Mark a media record as AI-generated."""
    if not media.is_generated:
        media.is_generated = True
        
        # Handle meta_info properly regardless of its current type
        if media.meta_info is None:
            meta_info = {"source": "DALL-E"}
        elif isinstance(media.meta_info, dict):
            meta_info = {"source": "DALL-E", **media.meta_info}
        elif isinstance(media.meta_info, str):
            try:
                meta_info = {"source": "DALL-E", **json.loads(media.meta_info)}
            except json.JSONDecodeError:
                meta_info = {"source": "DALL-E"}
        else:
            meta_info = {"source": "DALL-E"}
            
        media.meta_info = meta_info
        session.commit()
        print(f"Updated media record {media.id} (is_generated = True)")


def update_message_media_association(session: Session, msg_media: MessageMedia) -> None:
    """Update a message-media association to 'generated' type."""
    if msg_media.association_type != 'generated':
        msg_media.association_type = 'generated'
        session.commit()
        print(f"Updated message_media record {msg_media.id} (association_type = 'generated')")


def create_message_media_association(session: Session, 
                                    message_id: uuid.UUID, 
                                    media_id: uuid.UUID) -> None:
    """Create a new message-media association."""
    # Check if association already exists
    existing = session.query(MessageMedia).filter(
        and_(
            MessageMedia.message_id == message_id,
            MessageMedia.media_id == media_id
        )
    ).first()
    
    if existing:
        print(f"Association already exists between message {message_id} and media {media_id}")
        update_message_media_association(session, existing)
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
    print(f"Created new message_media association between message {message_id} and media {media_id}")


def main():
    """Main function to find and update DALL-E generated images."""
    # 1. Find all DALL-E generated images
    dalle_images = find_dalle_images()
    if not dalle_images:
        print("No DALL-E images found. Exiting.")
        return
    
    # 2. Extract file IDs and check if they exist in media table
    with get_session() as session:
        chatgpt_provider = session.query(Provider).filter_by(id=CHATGPT_PROVIDER_ID).first()
        if not chatgpt_provider:
            print(f"ChatGPT provider not found with ID {CHATGPT_PROVIDER_ID}")
            return
        
        # Find media records that might be DALL-E images but not marked as generated
        media_to_update = session.query(Media).filter(
            and_(
                Media.provider_id == CHATGPT_PROVIDER_ID,
                Media.is_generated == False,
                Media.file_path.like("%.webp")
            )
        ).all()
        
        print(f"Found {len(media_to_update)} .webp media records that may be DALL-E images")
        
        # 3. Update media records
        for media in media_to_update:
            update_media_record(session, media)
            
            # Find existing associations and update them
            existing_associations = find_existing_media_messages(session, media.id)
            for assoc in existing_associations:
                update_message_media_association(session, assoc)
        
        # 4. Find DALL-E tool messages to establish new associations
        tool_messages = find_dall_e_tool_messages(session)
        print(f"Found {len(tool_messages)} tool messages containing DALL-E references")
        
        for msg in tool_messages:
            # Try to extract file references from message content
            content = msg.content or ""
            file_refs = re.findall(r'file-([a-zA-Z0-9]+)', content)
            
            # Find assistant message that follows this tool message
            assistant_msg = session.query(Message).filter(
                and_(
                    Message.conversation_id == msg.conversation_id,
                    Message.role == 'assistant',
                    Message.created_at > msg.created_at
                )
            ).order_by(Message.created_at).first()
            
            # Look for media that matches file references
            for file_ref in file_refs:
                media = find_media_record(session, file_ref)
                if media:
                    # Associate with tool message
                    create_message_media_association(session, msg.id, media.id)
                    
                    # Also associate with the following assistant message if found
                    if assistant_msg:
                        create_message_media_association(session, assistant_msg.id, media.id)
                    
                    # Update media record
                    update_media_record(session, media)
        
        print("DALL-E image update completed!")


if __name__ == "__main__":
    main()