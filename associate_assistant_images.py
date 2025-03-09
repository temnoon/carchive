#!/usr/bin/env python3
"""
Script to associate DALL-E generated images with assistant messages.
Based on the finding that images need to be associated with assistant messages
that generated them, not just the tool messages.
"""
from carchive.database.session import get_session
from carchive.database.models import Message, Media, MessageMedia
import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_dalle_images():
    """Find all DALL-E generated images (.webp files marked as generated)."""
    with get_session() as session:
        images = session.query(Media).filter(
            Media.is_generated == True,
            Media.file_path.like('%.webp')
        ).all()
        
        logger.info(f"Found {len(images)} DALL-E generated images")
        return images

def find_messages_mentioning_dalle():
    """Find messages that explicitly mention DALL-E in their content."""
    with get_session() as session:
        messages = session.query(Message).filter(
            Message.content.ilike('%DALL-E%') | 
            Message.content.ilike('%generate%image%') |
            Message.content.ilike('%create%image%')
        ).all()
        
        logger.info(f"Found {len(messages)} messages mentioning DALL-E or image generation")
        return messages

def find_assistant_messages_after_user_request(user_message_id):
    """Find the next assistant message after a user's request for image generation."""
    with get_session() as session:
        user_msg = session.query(Message).filter(Message.id == user_message_id).first()
        if not user_msg or not user_msg.conversation_id:
            return None
        
        # Find the next assistant message in the same conversation
        next_assistant = session.query(Message).filter(
            Message.conversation_id == user_msg.conversation_id,
            Message.role == 'assistant',
            Message.created_at > user_msg.created_at
        ).order_by(Message.created_at).first()
        
        return next_assistant

def associate_images_with_messages():
    """Associate DALL-E images with both tool messages and assistant messages."""
    with get_session() as session:
        # Count of associations created
        tool_associations = 0
        assistant_associations = 0
        
        # Find all DALL-E images without associations
        orphaned_images = []
        all_images = find_dalle_images()
        
        for img in all_images:
            # Check if this image already has associations
            existing_links = session.query(MessageMedia).filter(
                MessageMedia.media_id == img.id
            ).all()
            
            if not existing_links:
                orphaned_images.append(img)
        
        logger.info(f"Found {len(orphaned_images)} orphaned DALL-E images")
        
        # For each message mentioning DALL-E, check if it should be associated with images
        dalle_messages = find_messages_mentioning_dalle()
        
        for msg in dalle_messages:
            # Skip if not user or assistant message
            if msg.role not in ['user', 'assistant']:
                continue
                
            # For user messages, find the next assistant response
            if msg.role == 'user':
                assistant_msg = find_assistant_messages_after_user_request(msg.id)
                if assistant_msg:
                    # If we have orphaned images, associate them with this assistant message
                    if orphaned_images:
                        # Take the first orphaned image
                        img = orphaned_images.pop(0)
                        
                        # Create association
                        association = MessageMedia(
                            message_id=assistant_msg.id,
                            media_id=img.id,
                            association_type='generated'
                        )
                        session.add(association)
                        assistant_associations += 1
                        logger.info(f"Associated image {img.id} with assistant message {assistant_msg.id}")
            
            # For assistant messages that generated images, associate directly
            elif msg.role == 'assistant' and 'generate' in (msg.content or '').lower():
                # If we have orphaned images, associate them with this assistant message
                if orphaned_images:
                    # Take the first orphaned image
                    img = orphaned_images.pop(0)
                    
                    # Create association
                    association = MessageMedia(
                        message_id=msg.id,
                        media_id=img.id,
                        association_type='generated'
                    )
                    session.add(association)
                    assistant_associations += 1
                    logger.info(f"Associated image {img.id} with assistant message {msg.id}")
        
        # Commit the changes
        session.commit()
        
        logger.info(f"Created {tool_associations} tool message associations")
        logger.info(f"Created {assistant_associations} assistant message associations")
        logger.info(f"Still have {len(orphaned_images)} orphaned DALL-E images")

def main():
    """Main function to associate DALL-E images with assistant messages."""
    logger.info("Starting association of DALL-E images with assistant messages")
    associate_images_with_messages()
    logger.info("Completed association process")

if __name__ == "__main__":
    main()