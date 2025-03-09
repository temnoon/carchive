#!/usr/bin/env python3
"""
Script to associate DALL-E generated images with their corresponding messages.

This script:
1. Finds tool messages containing 'DALL-E' references
2. Associates them with the correct image files
3. Also links the assistant messages that follow the tool messages to the same images

Usage:
    python scripts/fix_dalle/associate_images.py

"""
import os
import re
import uuid
from pathlib import Path
import json
from typing import List, Dict, Tuple, Optional, Set

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import Media, Message, MessageMedia


def find_dalle_tool_messages(session: Session) -> List[Message]:
    """Find all tool messages that mention DALL-E."""
    return session.query(Message).filter(
        and_(
            Message.role == 'tool',
            or_(
                Message.content.ilike('%DALL-E%'),
                Message.content.ilike('%DALLE%'),
                Message.content.ilike('%Image generation%')
            )
        )
    ).all()


def find_next_assistant_message(session: Session, tool_message: Message) -> Optional[Message]:
    """Find the assistant message that follows a tool message in the same conversation."""
    return session.query(Message).filter(
        and_(
            Message.conversation_id == tool_message.conversation_id,
            Message.role == 'assistant',
            Message.created_at > tool_message.created_at
        )
    ).order_by(Message.created_at).first()


def extract_file_ids_from_content(content: str) -> List[str]:
    """Extract file IDs from message content."""
    # Look for patterns like "file-ABC123" or similar
    file_ids = re.findall(r'file-([a-zA-Z0-9]+)', content)
    return file_ids


def find_media_by_original_id(session: Session, file_id: str) -> Optional[Media]:
    """Find a media record by its original_file_id."""
    return session.query(Media).filter(
        Media.original_file_id.ilike(f"%{file_id}%")
    ).first()


def get_existing_associations(session: Session, message_id: uuid.UUID) -> Set[uuid.UUID]:
    """Get the set of media IDs already associated with a message."""
    associations = session.query(MessageMedia).filter(
        MessageMedia.message_id == message_id
    ).all()
    return {assoc.media_id for assoc in associations}


def create_message_media_association(
    session: Session, 
    message_id: uuid.UUID, 
    media_id: uuid.UUID,
    association_type: str = 'generated'
) -> None:
    """Create a new message-media association if it doesn't exist."""
    # Check if association already exists
    existing = session.query(MessageMedia).filter(
        and_(
            MessageMedia.message_id == message_id,
            MessageMedia.media_id == media_id
        )
    ).first()
    
    if existing:
        # Update association type if needed
        if existing.association_type != association_type:
            existing.association_type = association_type
            session.commit()
            print(f"Updated association type for message {message_id} and media {media_id}")
        return
    
    # Create new association
    new_assoc = MessageMedia(
        id=uuid.uuid4(),
        message_id=message_id,
        media_id=media_id,
        association_type=association_type
    )
    session.add(new_assoc)
    session.commit()
    print(f"Created new association between message {message_id} and media {media_id}")


def main():
    """Main function to associate DALL-E images with messages."""
    with get_session() as session:
        # Find all tool messages containing DALL-E references
        tool_messages = find_dalle_tool_messages(session)
        print(f"Found {len(tool_messages)} DALL-E tool messages")
        
        # Track statistics
        total_associations = 0
        associated_tool_messages = 0
        associated_assistant_messages = 0
        
        # Process each tool message
        for tool_msg in tool_messages:
            # Extract file IDs from message content
            content = tool_msg.content or ""
            file_ids = extract_file_ids_from_content(content)
            
            if not file_ids:
                print(f"No file IDs found in tool message {tool_msg.id}")
                continue
            
            # Find the associated media records
            message_associated = False
            for file_id in file_ids:
                media = find_media_by_original_id(session, file_id)
                if media:
                    # Associate with tool message
                    create_message_media_association(session, tool_msg.id, media.id)
                    total_associations += 1
                    message_associated = True
                    
                    # Find and associate with the following assistant message
                    assistant_msg = find_next_assistant_message(session, tool_msg)
                    if assistant_msg:
                        create_message_media_association(session, assistant_msg.id, media.id)
                        total_associations += 1
                        associated_assistant_messages += 1
            
            if message_associated:
                associated_tool_messages += 1
        
        print(f"Created {total_associations} total associations")
        print(f"Associated {associated_tool_messages} tool messages with images")
        print(f"Associated {associated_assistant_messages} assistant messages with images")
        
        # Now find all .webp media that are marked as generated but have no message associations
        generated_webp = session.query(Media).filter(
            and_(
                Media.is_generated == True,
                Media.file_path.like("%.webp")
            )
        ).all()
        
        orphaned_media = []
        for media in generated_webp:
            associations = session.query(MessageMedia).filter(
                MessageMedia.media_id == media.id
            ).count()
            
            if associations == 0:
                orphaned_media.append(media)
        
        print(f"Found {len(orphaned_media)} orphaned DALL-E images with no message associations")
        
        # Optionally, try to match orphaned media with messages based on content or conversation context
        # This would require additional analysis and is left as a future enhancement
        
        print("Image association process completed!")


if __name__ == "__main__":
    main()