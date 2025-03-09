#!/usr/bin/env python
"""
Fix DALL-E image references in the carchive database.

This script:
1. Removes placeholder media records created by our previous fix
2. Scans chat2/dalle-generations/ for DALL-E images
3. Processes message content to find [Asset: file-ID] references
4. Copies the actual image files to the media/ folder
5. Creates proper media records with real file content
6. Links media to messages via the message_media table
"""

import argparse
import hashlib
import os
import re
import shutil
import uuid
from typing import Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import Json, RealDictCursor

# Regular expression to find DALL-E asset references
ASSET_PATTERN = r'\[Asset: (file-[a-zA-Z0-9]+)\]'

def calculate_checksum(file_path: str) -> str:
    """Calculate SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            h.update(chunk)
    return h.hexdigest()

def guess_mime_type(file_path: str) -> str:
    """Guess mime type from file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.pdf': 'application/pdf',
    }
    return mime_types.get(ext, 'application/octet-stream')

def find_dalle_images(dalle_dir: str) -> Dict[str, str]:
    """Find DALL-E images and map file IDs to file paths."""
    image_map = {}
    # Pattern like file-0VjolCE3e2SHb7cgOyjkvIY4-7ab6e192-8108-474b-b2a7-389fe5c80910.webp
    pattern = re.compile(r'file-([a-zA-Z0-9]+)')
    
    if not os.path.exists(dalle_dir):
        print(f"DALL-E directory not found: {dalle_dir}")
        return image_map
    
    for filename in os.listdir(dalle_dir):
        match = pattern.search(filename)
        if match:
            file_id = f"file-{match.group(1)}"
            image_map[file_id] = os.path.join(dalle_dir, filename)
    
    print(f"Found {len(image_map)} DALL-E images in {dalle_dir}")
    return image_map

def remove_placeholder_records(conn) -> int:
    """Remove placeholder media records created by our previous fix."""
    with conn.cursor() as cursor:
        # First remove message_media associations
        cursor.execute("""
            DELETE FROM message_media WHERE media_id IN (
                SELECT id FROM media WHERE meta_info->>'placeholder' = 'true'
            );
        """)
        deleted_assocs = cursor.rowcount
        
        # Then remove media records
        cursor.execute("""
            DELETE FROM media WHERE meta_info->>'placeholder' = 'true';
        """)
        deleted_media = cursor.rowcount
        
        conn.commit()
        
    print(f"Removed {deleted_assocs} message_media associations and {deleted_media} placeholder media records")
    return deleted_media

def scan_messages_for_asset_refs(conn) -> Dict[str, List[str]]:
    """
    Scan message content for DALL-E asset references.
    Returns a dictionary mapping file IDs to lists of message IDs.
    """
    file_refs = {}
    
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("""
            SELECT id, content FROM messages WHERE content LIKE '%Asset: file-%';
        """)
        messages = cursor.fetchall()
        
        for msg in messages:
            message_id = msg['id']
            content = msg['content']
            
            if content:
                matches = re.findall(ASSET_PATTERN, content)
                for file_id in matches:
                    if file_id not in file_refs:
                        file_refs[file_id] = []
                    file_refs[file_id].append(message_id)
    
    print(f"Found {len(file_refs)} unique file IDs referenced in messages")
    return file_refs

def process_dalle_images(conn, image_map: Dict[str, str], file_refs: Dict[str, List[str]], 
                        media_dir: str = './media', provider_id: str = '11111111-1111-1111-1111-111111111111') -> Tuple[int, int]:
    """
    Process DALL-E images:
    1. Copy images to media directory
    2. Create media records
    3. Link media to messages
    
    Returns (created_media, created_links) counts.
    """
    media_created = 0
    links_created = 0
    
    # Ensure media directory exists
    os.makedirs(media_dir, exist_ok=True)
    
    with conn.cursor() as cursor:
        for file_id, message_ids in file_refs.items():
            # Skip if we don't have the file
            if file_id not in image_map:
                print(f"No image found for {file_id}, referenced in {len(message_ids)} messages")
                continue
                
            source_path = image_map[file_id]
            
            # Generate new UUID for media record
            media_id = str(uuid.uuid4())
            
            # Get file extension
            _, ext = os.path.splitext(source_path)
            
            # Create target path
            target_path = os.path.join(media_dir, f"{media_id}{ext}")
            
            # Copy file
            try:
                shutil.copy2(source_path, target_path)
                print(f"Copied {file_id} to {target_path}")
            except Exception as e:
                print(f"Error copying {source_path}: {e}")
                continue
                
            # Calculate file metadata
            file_size = os.path.getsize(target_path)
            checksum = calculate_checksum(target_path)
            mime_type = guess_mime_type(target_path)
            
            # Create media record
            cursor.execute("""
                INSERT INTO media (
                    id, file_path, original_file_name, original_file_id,
                    provider_id, mime_type, file_size, checksum,
                    is_generated, media_type, meta_info
                ) VALUES (
                    %s, %s, %s, %s, 
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
            """, (
                media_id, target_path, os.path.basename(source_path), file_id,
                provider_id, mime_type, file_size, checksum,
                True, 'image', Json({'source': 'dalle', 'copied_from': source_path})
            ))
            media_created += 1
            
            # Create message_media associations
            for message_id in message_ids:
                # Check if association already exists
                cursor.execute("""
                    SELECT id FROM message_media 
                    WHERE message_id = %s AND media_id = %s
                """, (message_id, media_id))
                
                if cursor.fetchone() is None:
                    # Create association
                    assoc_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO message_media (id, message_id, media_id, association_type)
                        VALUES (%s, %s, %s, %s)
                    """, (assoc_id, message_id, media_id, 'generated'))
                    links_created += 1
        
        conn.commit()
    
    return media_created, links_created

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Fix DALL-E image references in carchive')
    parser.add_argument('--dalle-dir', default='./chat2/dalle-generations', 
                      help='Directory containing DALL-E images')
    parser.add_argument('--media-dir', default='./media',
                      help='Directory to store media files')
    parser.add_argument('--db-host', default='localhost', 
                      help='Database host')
    parser.add_argument('--db-port', default=5432, type=int,
                      help='Database port')
    parser.add_argument('--db-name', default='carchive04_db',
                      help='Database name')
    parser.add_argument('--db-user', default='postgres',
                      help='Database user')
    parser.add_argument('--db-password', default='postgres',
                      help='Database password')
    parser.add_argument('--provider', default='11111111-1111-1111-1111-111111111111',
                      help='Provider ID for ChatGPT')
    args = parser.parse_args()
    
    # Connect to database
    conn = psycopg2.connect(
        host=args.db_host,
        port=args.db_port,
        dbname=args.db_name,
        user=args.db_user,
        password=args.db_password
    )
    
    try:
        # Step 1: Remove placeholder records
        removed = remove_placeholder_records(conn)
        
        # Step 2: Find DALL-E images
        image_map = find_dalle_images(args.dalle_dir)
        
        # Step 3: Scan messages for asset references
        file_refs = scan_messages_for_asset_refs(conn)
        
        # Step 4: Process DALL-E images
        media_created, links_created = process_dalle_images(
            conn, image_map, file_refs, args.media_dir, args.provider
        )
        
        print(f"\nSummary:")
        print(f"- Removed {removed} placeholder media records")
        print(f"- Found {len(image_map)} DALL-E images in {args.dalle_dir}")
        print(f"- Found {len(file_refs)} file IDs referenced in messages")
        print(f"- Created {media_created} media records with real content")
        print(f"- Created {links_created} message-media associations")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()