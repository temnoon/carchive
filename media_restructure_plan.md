# Media Restructuring Plan for Carchive

## Problem Statement

The current media storage system in Carchive has several issues:

1. Media files are currently renamed to UUIDs when imported, making it difficult to trace back to original files
2. The matching logic using partial file IDs (first 8 chars) may be causing incorrect file associations
3. There are inconsistencies between archives, with some files appearing in multiple archives with different names
4. Images are sometimes being rendered incorrectly in conversations

## Proposed Solution

Create a new media storage and retrieval system with the following characteristics:

1. **Preserve Original Filenames**: Do not rename files during import
2. **Hierarchical Storage**: Organize files in a structured directory hierarchy
3. **Robust Identification**: Use full file IDs and checksums for identification
4. **Database Redesign**: Update the media table schema to support the new system
5. **Graceful Fallback**: Handle missing files robustly

## Implementation Plan

### 1. Database Schema Changes

These changes should be implemented via an Alembic migration:

```python
"""Add new fields to Media table for improved file tracking

Revision ID: xxxx
Revises: previous_revision
Create Date: 2025-03-xx

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    # Add new columns to the media table
    op.add_column('media', sa.Column('archive_source', sa.String(), nullable=True))
    op.add_column('media', sa.Column('relative_path', sa.String(), nullable=True))
    op.add_column('media', sa.Column('original_path', sa.String(), nullable=True))
    
    # Create new indexes
    op.create_index('ix_media_original_file_id', 'media', ['original_file_id'], unique=False)
    op.create_index('ix_media_checksum', 'media', ['checksum'], unique=False)

def downgrade():
    # Remove new columns from the media table
    op.drop_column('media', 'archive_source')
    op.drop_column('media', 'relative_path')
    op.drop_column('media', 'original_path')
    
    # Drop indexes
    op.drop_index('ix_media_original_file_id', 'media')
    op.drop_index('ix_media_checksum', 'media')
```

### 2. New File Organization Structure

```
media/
├── chatgpt/                 # By provider
│   ├── chat/                # By archive/source
│   │   └── file-{ID}-{name} # Original filename
│   ├── chat2/
│   │   └── ...
│   └── chat3/
│       └── ...
├── claude/
│   └── ...
└── shared/                  # For files referenced from multiple sources
    └── ...
```

### 3. Media Import/Migration Adapter Updates

1. Update `ChatGPTAdapter` class in `chatgpt_adapter.py`:
   - Change file handling logic to preserve original filenames
   - Implement optional deduplication by checksum
   - Implement file copying/linking rather than renaming

2. Create a migration tool to move existing files from the current structure to the new one

### 4. Media Access Service Updates

1. Update `MediaService` class to:
   - Look up files by both UUID and original file ID
   - Use a fallback mechanism to handle missing files
   - Support checksum-based deduplication

### 5. GUI/API Updates

1. Update API endpoints to:
   - Return more metadata about media files
   - Support viewing original filenames
   - Support viewing archive source information

2. Update GUI:
   - Add display for original filenames/IDs
   - Add indication of media source/archive
   - Implement better error handling for missing files

## Implementation Sequence

1. First run the analysis script to verify the consistency of file IDs across archives
2. Apply database schema changes (alembic migration)
3. Create a backup of the current media directory
4. Implement the new file organization structure and media access service
5. Create and test the migration tool
6. Run migration in a test environment
7. Validate and fix any issues
8. Apply migration to production

## Key Code Changes

### 1. Updated ChatGPT Adapter

Key changes to `chatgpt_adapter.py`:

```python
def _process_attachment(self, attachment: Dict, message_id: str, position: int) -> Optional[Dict]:
    """Process a message attachment and return a media record."""
    attachment_id = attachment.get('id')
    if not attachment_id:
        return None
        
    # Determine original file path
    original_filename = attachment.get('name', '')
    file_path = None
    
    # ChatGPT archive files follow a pattern like "file-{ID}-{filename}"
    for filename in os.listdir(self.media_dir):
        if filename.startswith("file-") and attachment_id in filename:
            file_path = os.path.join(self.media_dir, filename)
            logger.info(f"Found media file for attachment {attachment_id}: {filename}")
            break
    
    if not file_path:
        logger.warning(f"File not found for attachment {attachment_id}")
        return None
        
    # Create a UUID for the media item
    media_id = str(uuid.uuid4())
    
    # Calculate checksum
    checksum = self._calculate_file_checksum(file_path)
    
    # Determine mimetype from attachment or filename
    mime_type = attachment.get('mimeType', self._guess_mime_type(file_path))
    
    # Preserve original filename structure
    original_name = os.path.basename(file_path)
    archive_source = os.path.basename(self.media_dir)
    relative_path = os.path.join(archive_source, original_name)
    
    # Copy to target directory with original name
    target_dir = os.path.join(self.target_media_dir, archive_source)
    target_path = os.path.join(target_dir, original_name)
    
    # Copy file if it doesn't exist yet
    if not os.path.exists(target_path):
        try:
            import shutil
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(file_path, target_path)
        except Exception as e:
            logger.error(f"Failed to copy file {file_path}: {e}")
            return None
    
    # Create media record
    media_item = {
        'id': media_id,
        'file_path': target_path,
        'original_file_name': original_filename,
        'original_file_id': attachment_id,
        'provider_id': CHATGPT_PROVIDER_ID,
        'mime_type': mime_type,
        'file_size': os.path.getsize(file_path),
        'checksum': checksum,
        'is_generated': False,
        'source_url': None,
        'archive_source': archive_source,
        'relative_path': relative_path,
        'original_path': file_path,
        'meta_info': json.dumps(attachment)
    }
    
    # Create message_media relation
    message_media = {
        'id': str(uuid.uuid4()),
        'message_id': message_id,
        'media_id': media_id,
        'association_type': 'attachment',
        'position': position,
        'meta_info': json.dumps({})
    }
    
    # Store mapping for future reference
    self.media_mapping[attachment_id] = media_id
    
    return {
        'media': media_item,
        'message_media': message_media
    }
```

### 2. Updated Media Service

Add a method to find media by original ID:

```python
def get_media_by_original_id(self, original_id: str, archive_source: Optional[str] = None) -> Optional[Media]:
    """Find media by its original ID, optionally filtered by archive source."""
    query = self.session.query(Media).filter(Media.original_file_id == original_id)
    
    if archive_source:
        query = query.filter(Media.archive_source == archive_source)
    
    return query.first()
```

Add fallback logic for media lookup:

```python
def get_media_file_path(self, media_id: str) -> Optional[str]:
    """Get the path to a media file, with fallback mechanisms."""
    # Try to get the media by ID first
    media = self.get_media(media_id)
    
    if media and os.path.exists(media.file_path):
        return media.file_path
        
    # If media exists but file is missing, try to find it by original ID
    if media and media.original_file_id:
        # Look through all archive sources
        for archive in ['chat3', 'chat2', 'chat']:  # Priority order
            alt_media = self.get_media_by_original_id(media.original_file_id, archive)
            if alt_media and os.path.exists(alt_media.file_path):
                # Log this fallback for later analysis
                logger.info(f"Media fallback: {media_id} -> {alt_media.id} ({archive})")
                return alt_media.file_path
    
    # No file found
    logger.warning(f"Media file not found: {media_id}")
    return None
```

### 3. Migration Script

Create a new script to migrate existing media files:

```python
# migrate_media.py
import os
import uuid
import hashlib
import shutil
from typing import Dict, List
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from carchive.database.models import Media
from carchive.database.session import get_session

logger = logging.getLogger(__name__)

def calculate_checksum(file_path: str) -> str:
    """Calculate MD5 checksum for a file."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def migrate_media_files(source_dir: str, target_dir: str, archive_name: str = None):
    """
    Migrate media files from the old structure to the new structure.
    
    Args:
        source_dir: Current media directory with UUID-named files
        target_dir: New media directory organized by archive
        archive_name: Name of the archive source (e.g., 'chat', 'chat2')
    """
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    
    # Get all media records from the database
    with get_session() as session:
        media_records = session.query(Media).all()
        
        for media in media_records:
            source_path = media.file_path
            
            # Skip if source file doesn't exist
            if not os.path.exists(source_path):
                logger.warning(f"Source file not found: {source_path}")
                continue
            
            # Determine target path
            if media.original_file_id and media.original_file_name:
                # Try to reconstruct original filename
                original_name = f"file-{media.original_file_id}-{media.original_file_name}"
            else:
                # Fallback to UUID filename
                original_name = os.path.basename(source_path)
            
            # Create subdirectory for this archive
            archive_dir = os.path.join(target_dir, archive_name or 'unknown')
            os.makedirs(archive_dir, exist_ok=True)
            
            target_path = os.path.join(archive_dir, original_name)
            
            # Copy file
            try:
                shutil.copy2(source_path, target_path)
                logger.info(f"Copied: {source_path} -> {target_path}")
                
                # Update database record
                media.file_path = target_path
                media.archive_source = archive_name
                media.relative_path = os.path.join(archive_name or 'unknown', original_name)
                
                # Recalculate checksum
                media.checksum = calculate_checksum(target_path)
                
                session.add(media)
            except Exception as e:
                logger.error(f"Failed to copy {source_path}: {e}")
        
        # Commit all changes
        session.commit()
```

## Testing Plan

1. Create a small test dataset from each archive
2. Apply the schema changes to a test database
3. Run the migration on the test dataset
4. Verify file integrity and database consistency
5. Test media retrieval with the new service
6. Test fallback mechanisms with missing files

## Rollback Plan

1. Keep a backup of the original media directory
2. Create a database backup before migration
3. Prepare a rollback script that restores the original media paths in the database

## Conclusion

This restructuring will improve the reliability of media file handling in Carchive by:

1. Preserving original filenames for better traceability
2. Using full file IDs instead of partial IDs to prevent collisions
3. Adding checksums for integrity verification
4. Implementing fallback mechanisms for robustness
5. Providing better organization by archive source

The migration can be done incrementally, starting with a thorough analysis and testing on small datasets before applying to the full production data.
