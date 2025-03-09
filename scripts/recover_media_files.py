#!/usr/bin/env python3
"""
Script to recover missing or empty media files by searching for original content
in chat archives and copying to the media folder with the correct UUID filename.
"""

import os
import sys
import glob
import shutil
import logging
import psycopg2
from pathlib import Path
from datetime import datetime

# Configure logging
log_filename = f"media_recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database connection parameters
DB_NAME = "carchive04_db"
DB_USER = "carchive_app"
DB_PASSWORD = "carchive_pass"  # Adjust if needed
DB_HOST = "localhost"
DB_PORT = "5432"

# File paths
MEDIA_DIR = "./media"
SEARCH_PATHS = [
    "./chat2",
    "./chat2/dalle-generations",
    "./chat",
    "./chat/dalle-generations"
]

def connect_to_db():
    """Connect to the database and return connection object"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        logger.info("Connected to database successfully")
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        sys.exit(1)

def get_all_media_records(conn):
    """Get all records from the media table"""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, original_file_id, original_file_name, media_type, file_size, file_path, mime_type
            FROM media
        """)
        media_records = cursor.fetchall()
        logger.info(f"Retrieved {len(media_records)} media records from database")
        return media_records
    except Exception as e:
        logger.error(f"Error retrieving media records: {e}")
        cursor.close()
        sys.exit(1)
    finally:
        cursor.close()

def find_original_file(original_file_id, original_file_name):
    """
    Search for the original file in various locations
    Returns the path if found, None otherwise
    """
    # Skip if original_file_id is None
    if not original_file_id:
        return None
    
    # Get the file ID without the 'file-' prefix if it exists
    search_id = original_file_id
    if search_id.startswith("file-"):
        search_id = search_id[5:]  # Remove 'file-' prefix
    
    # Check all search paths
    for search_path in SEARCH_PATHS:
        # First try with the file ID
        pattern = f"{search_path}/file-*{search_id}*"
        matching_files = glob.glob(pattern)
        
        for file_path in matching_files:
            # Check if file exists and has content
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path
        
        # If we have an original filename, try that too
        if original_file_name:
            # Try to match by original filename
            pattern = f"{search_path}/*{original_file_name}*"
            matching_files = glob.glob(pattern)
            
            for file_path in matching_files:
                # Check if file exists and has content
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    return file_path
    
    return None

def get_extension_from_filename(filename):
    """Extract extension from filename"""
    if not filename:
        return ""
    parts = filename.split('.')
    if len(parts) > 1:
        return parts[-1].lower()
    return ""

def get_extension_from_mime_type(mime_type):
    """Get file extension from MIME type"""
    if not mime_type:
        return ""
        
    # Common MIME type to extension mappings
    mime_map = {
        'image/jpeg': 'jpg',
        'image/jpg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp',
        'image/svg+xml': 'svg',
        'application/pdf': 'pdf',
        'text/plain': 'txt',
        'text/html': 'html',
        'text/css': 'css',
        'text/javascript': 'js',
        'application/json': 'json',
        'application/zip': 'zip'
    }
    
    return mime_map.get(mime_type.lower(), "")

def process_media_records():
    """Process all media records and recover missing/empty files"""
    conn = connect_to_db()
    media_records = get_all_media_records(conn)
    
    stats = {
        "total": len(media_records),
        "already_valid": 0,
        "recovered": 0,
        "not_found": 0,
        "errors": 0
    }
    
    for record in media_records:
        media_id, original_file_id, original_file_name, media_type, file_size, file_path, mime_type = record
        
        # Skip non-image files if needed
        if media_type != "image" and media_type != "file":
            logger.info(f"Skipping non-image/file media type: {media_id} ({media_type})")
            continue
        
        # Get extension from original filename or mime type
        extension = get_extension_from_filename(original_file_name) or get_extension_from_mime_type(mime_type)
        
        # Determine target file path
        target_file = f"{MEDIA_DIR}/{media_id}"
        if extension:
            target_file = f"{target_file}.{extension}"
        
        # Check if the target file already exists and has content
        if os.path.exists(target_file) and os.path.getsize(target_file) > 0:
            logger.info(f"File already valid: {target_file}")
            stats["already_valid"] += 1
            continue
        
        # First, try to use the existing file_path if it's already set and the file exists
        if file_path and os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                
                # Copy the file
                shutil.copy2(file_path, target_file)
                logger.info(f"Recovered from file_path: {media_id} - Copied from {file_path} to {target_file}")
                stats["recovered"] += 1
                continue
            except Exception as e:
                logger.error(f"Error copying from file_path {file_path} to {target_file}: {e}")
                # Continue to other search methods
        
        # Search for original file
        original_file = find_original_file(original_file_id, original_file_name)
        
        if original_file:
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                
                # Copy the file
                shutil.copy2(original_file, target_file)
                logger.info(f"Recovered: {media_id} - Copied from {original_file} to {target_file}")
                stats["recovered"] += 1
            except Exception as e:
                logger.error(f"Error copying file {original_file} to {target_file}: {e}")
                stats["errors"] += 1
        else:
            logger.warning(f"Original file not found for media_id: {media_id}, original_file_id: {original_file_id}, original_file_name: {original_file_name}")
            stats["not_found"] += 1
    
    # Close the database connection
    conn.close()
    
    # Log summary statistics
    logger.info("=" * 50)
    logger.info("RECOVERY PROCESS COMPLETED")
    logger.info(f"Total media records: {stats['total']}")
    logger.info(f"Already valid files: {stats['already_valid']}")
    logger.info(f"Recovered files: {stats['recovered']}")
    logger.info(f"Files not found: {stats['not_found']}")
    logger.info(f"Errors encountered: {stats['errors']}")
    logger.info("=" * 50)
    
    return stats

if __name__ == "__main__":
    logger.info("Starting media file recovery process")
    
    # Ensure media directory exists
    os.makedirs(MEDIA_DIR, exist_ok=True)
    
    # Process all media records
    stats = process_media_records()
    
    # Exit with error code if any files were not found
    if stats["not_found"] > 0 or stats["errors"] > 0:
        logger.warning(f"Completed with {stats['not_found']} files not found and {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Recovery completed successfully")
        sys.exit(0)