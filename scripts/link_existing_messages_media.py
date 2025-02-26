#!/usr/bin/env python3
"""
Script to analyze and fix relationships between messages and media.
This script checks for media items that should be associated with messages
and creates links in the message_media association table.
"""

import logging
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection settings
DB_NAME = "carchive03_db"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_URL = f"postgresql://{DB_USER}@{DB_HOST}/{DB_NAME}"

def link_messages_and_media():
    """Link messages to their media items using file_id patterns."""
    try:
        # Connect to the database
        engine = create_engine(DB_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # 1. Get count of existing message-media associations
        count_query = text("SELECT COUNT(*) FROM message_media")
        existing_count = session.execute(count_query).scalar()
        logger.info(f"Current message-media associations: {existing_count}")
        
        # 2. Look for messages with media references in content
        logger.info("Analyzing message content for media references...")
        
        # Find messages with file references in their content
        messages_with_refs = session.execute(text("""
        SELECT id, content 
        FROM messages 
        WHERE content LIKE '%file-%' OR content LIKE '%media/%'
        """)).fetchall()
        
        logger.info(f"Found {len(messages_with_refs)} messages with potential media references")
        
        # 3. Find corresponding media items and link them
        association_count = 0
        for message_id, content in messages_with_refs:
            # Look for file IDs in format file-XXXX or mentions of media files
            import re
            file_ids = re.findall(r'file-([a-zA-Z0-9]{16,32})', content)
            
            for file_id in file_ids:
                # Find media with this original_file_id
                media_items = session.execute(text("""
                SELECT id FROM media WHERE original_file_id = :file_id
                """), {"file_id": file_id}).fetchall()
                
                for media_id, in media_items:
                    # Check if the association already exists
                    existing = session.execute(text("""
                    SELECT id FROM message_media 
                    WHERE message_id = :message_id AND media_id = :media_id
                    """), {"message_id": message_id, "media_id": media_id}).fetchone()
                    
                    if not existing:
                        # Create new association
                        session.execute(text("""
                        INSERT INTO message_media (id, message_id, media_id, association_type)
                        VALUES (:id, :message_id, :media_id, 'referenced')
                        """), {
                            "id": str(uuid.uuid4()),
                            "message_id": message_id,
                            "media_id": media_id,
                            
                        })
                        association_count += 1
        
        # 4. Link messages with media_id to their media
        logger.info("Linking messages with direct media_id references...")
        
        direct_links = session.execute(text("""
        INSERT INTO message_media (id, message_id, media_id, association_type)
        SELECT gen_random_uuid(), id, media_id, 'direct'
        FROM messages
        WHERE media_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM message_media 
            WHERE message_id = messages.id AND media_id = messages.media_id
        )
        RETURNING message_id
        """)).rowcount
        
        association_count += direct_links
        
        # 5. Commit changes
        session.commit()
        
        # Final count
        final_count = session.execute(count_query).scalar()
        logger.info(f"Added {association_count} new message-media associations")
        logger.info(f"Total message-media associations: {final_count}")
        
        # 6. Print stats
        media_count = session.execute(text("SELECT COUNT(*) FROM media")).scalar()
        message_count = session.execute(text("SELECT COUNT(*) FROM messages")).scalar()
        
        logger.info(f"Database has {media_count} media items and {message_count} messages")
        
        # 7. Count how many media items are now linked to messages
        linked_media = session.execute(text("""
        SELECT COUNT(DISTINCT media_id) FROM message_media
        """)).scalar()
        
        logger.info(f"{linked_media} media items are now linked to messages ({linked_media/media_count:.1%})")
        
        return True
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    if link_messages_and_media():
        logger.info("Media-message linking completed successfully!")
    else:
        logger.error("Media-message linking failed.")
        import sys
        sys.exit(1)