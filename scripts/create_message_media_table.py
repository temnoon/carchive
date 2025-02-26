#!/usr/bin/env python3
"""
Script to create a message_media association table and fix the schema issues.
"""

import os
import sys
import uuid
import logging
from sqlalchemy import create_engine, Column, ForeignKey, Table, MetaData, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, declarative_base

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection settings
DB_NAME = "carchive03_db"
DB_USER = "postgres"
DB_HOST = "localhost"
DB_URL = f"postgresql://{DB_USER}@{DB_HOST}/{DB_NAME}"

def create_message_media_table():
    """Create a new message_media association table and migrate existing relationships."""
    try:
        # Connect to the database
        engine = create_engine(DB_URL)
        Base = declarative_base()
        metadata = MetaData()
        
        # Reflect existing tables to ensure foreign keys work
        metadata.reflect(bind=engine)
        
        # Check if the message_media table already exists
        if 'message_media' in metadata.tables:
            logger.info("message_media table already exists, skipping creation")
        else:
            # Define the message_media association table
            message_media = Table(
                'message_media', 
                metadata,
                Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
                Column('message_id', UUID(as_uuid=True), ForeignKey('messages.id', ondelete='CASCADE'), nullable=False),
                Column('media_id', UUID(as_uuid=True), ForeignKey('media.id', ondelete='CASCADE'), nullable=False),
                Column('association_type', String, nullable=True)  # 'uploaded', 'generated', etc.
            )
            
            # Create the table
            logger.info("Creating message_media association table...")
            message_media.create(engine)
            logger.info("Table created successfully!")

        # Create a session to work with
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Migrate existing relationships to the new association table
        logger.info("Migrating existing message-media relationships...")
        
        # Use text() to properly handle SQL statements
        from sqlalchemy import text
        
        # First, handle media with message_id (uploaded media)
        session.execute(text("""
        INSERT INTO message_media (id, message_id, media_id, association_type)
        SELECT gen_random_uuid(), message_id, id, 'uploaded'
        FROM media
        WHERE message_id IS NOT NULL
        """))
        
        # Then handle media with linked_message_id (generated media)
        session.execute(text("""
        INSERT INTO message_media (id, message_id, media_id, association_type)
        SELECT gen_random_uuid(), linked_message_id, id, 'generated'
        FROM media
        WHERE linked_message_id IS NOT NULL AND linked_message_id != message_id
        """))
        
        # Commit the changes
        session.commit()
        logger.info("Migration completed successfully!")
        
        return True
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    if create_message_media_table():
        logger.info("Message-media association table created and data migrated successfully!")
    else:
        logger.error("Failed to create message-media association table.")
        sys.exit(1)