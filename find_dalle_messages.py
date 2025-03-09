#!/usr/bin/env python3
"""
Script to find messages related to DALL-E image generation.
"""
from carchive.database.session import get_session
from carchive.database.models import Message, Media, MessageMedia
import json

def main():
    """Find messages that might contain DALL-E image generation requests."""
    with get_session() as session:
        # First approach: Find .webp files that are marked as generated
        print("=== Finding DALL-E Generated Images ===")
        generated_images = session.query(Media).filter(
            Media.is_generated == True,
            Media.file_path.like('%.webp')
        ).limit(10).all()
        
        print(f"Found {len(generated_images)} DALL-E generated images")
        
        for i, img in enumerate(generated_images):
            print(f"\n--- Image {i+1} ID: {img.id} ---")
            print(f"Path: {img.file_path}")
            
            # Check if this image has message associations
            msg_links = session.query(MessageMedia).filter(
                MessageMedia.media_id == img.id
            ).all()
            
            if msg_links:
                print(f"  Has {len(msg_links)} message associations:")
                for link in msg_links:
                    msg = session.query(Message).filter(Message.id == link.message_id).first()
                    if msg:
                        print(f"    - Message {msg.id} | role: {msg.role} | association_type: {link.association_type}")
                        print(f"      Content excerpt: {(msg.content or '')[:100]}...")
            else:
                print("  No message associations")
        
        # Second approach: Look for messages explicitly mentioning DALL-E
        print("\n\n=== Finding Messages Mentioning DALL-E ===")
        dalle_msgs = session.query(Message).filter(
            Message.content.ilike('%DALL-E%')
        ).limit(10).all()
        
        print(f"Found {len(dalle_msgs)} messages mentioning DALL-E")
        
        for i, msg in enumerate(dalle_msgs):
            print(f"\n--- Message {i+1} ID: {msg.id} ---")
            print(f"Role: {msg.role}")
            print(f"Content (excerpt): {(msg.content or '')[:200]}...")
            
            # Check if this message has associated media
            media_links = session.query(MessageMedia).filter(
                MessageMedia.message_id == msg.id
            ).all()
            
            if media_links:
                print(f"  Has {len(media_links)} associated media:")
                for link in media_links:
                    media = session.query(Media).filter(Media.id == link.media_id).first()
                    if media:
                        print(f"    - {media.id} | {media.file_path} | is_generated: {media.is_generated} | association_type: {link.association_type}")
            else:
                print("  No associated media")

if __name__ == "__main__":
    main()