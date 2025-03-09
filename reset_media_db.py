#!/usr/bin/env python
"""
This script resets the media-related database records to prepare for re-importing 
media files from the chat3 archive.
"""

import os
import sys
import logging
import argparse
from sqlalchemy import text
from carchive.database.session import get_session
from carchive.database.models import Media, MessageMedia

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("media_reset.log")
    ]
)
logger = logging.getLogger("media_reset")

def reset_media_records(dry_run=True):
    """
    Reset media-related records in the database.
    
    Args:
        dry_run: If True, show what would be deleted without making changes
    
    Returns:
        Dict with deletion statistics
    """
    stats = {
        "media_associations_deleted": 0,
        "media_records_deleted": 0
    }
    
    with get_session() as session:
        # First count how many records we'd delete
        message_media_count = session.query(MessageMedia).count()
        media_count = session.query(Media).count()
        
        logger.info(f"Found {message_media_count} message-media associations")
        logger.info(f"Found {media_count} media records")
        
        if dry_run:
            logger.info("DRY RUN - No records will be deleted")
            logger.info(f"Would delete {message_media_count} message-media associations")
            logger.info(f"Would delete {media_count} media records")
            return stats
        
        # First delete message-media associations
        try:
            result = session.execute(text("DELETE FROM message_media"))
            stats["media_associations_deleted"] = result.rowcount
            logger.info(f"Deleted {stats['media_associations_deleted']} message-media associations")
        except Exception as e:
            logger.error(f"Error deleting message-media associations: {e}")
            session.rollback()
            return stats
        
        # Then delete media records
        try:
            result = session.execute(text("DELETE FROM media"))
            stats["media_records_deleted"] = result.rowcount
            logger.info(f"Deleted {stats['media_records_deleted']} media records")
        except Exception as e:
            logger.error(f"Error deleting media records: {e}")
            session.rollback()
            return stats
        
        # Commit the changes
        session.commit()
        logger.info("Committed database changes")
        
    return stats

def main():
    parser = argparse.ArgumentParser(description="Reset media-related database records")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without making changes")
    args = parser.parse_args()
    
    logger.info(f"Starting media database reset (dry_run={args.dry_run})")
    
    stats = reset_media_records(dry_run=args.dry_run)
    
    if args.dry_run:
        logger.info("\nDRY RUN SUMMARY:")
        logger.info(f"Would delete {stats['media_associations_deleted']} message-media associations")
        logger.info(f"Would delete {stats['media_records_deleted']} media records")
        logger.info("No changes made to the database")
    else:
        logger.info("\nRESET SUMMARY:")
        logger.info(f"Deleted {stats['media_associations_deleted']} message-media associations")
        logger.info(f"Deleted {stats['media_records_deleted']} media records")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())