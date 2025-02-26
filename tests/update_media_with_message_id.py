#!/usr/bin/env python3
"""
Update media records by correlating them with messages based on file ID extraction.

For each Media record (with media_type == "image") that does not have a "source_message_id"
in its meta_info, this script:
  1. Extracts the file ID from the media file's path (i.e. the substring immediately after "file-" or "file_"
     and before the next hyphen).
  2. Searches for a Message (of a given role, default "tool") whose content contains that file ID.
  3. If found, updates the media record’s meta_info to include the key "source_message_id" set to that Message’s ID.

Usage:
  python tests/update_media_with_message_id.py --limit 100 --role tool
"""

import re
import argparse
from carchive.database.session import get_session
from carchive.database.models import Media, Message

def extract_file_id_from_filepath(filepath: str):
    """
    Extracts the file ID from a file path.

    The file ID is assumed to be the string immediately after "file-" or "file_"
    and ending at the next hyphen.

    For example, from:
      "chat/file-Bi1QJn47A71vD7Y2L6gT6y-Sunday costume rentals01.JPG"
    it will extract:
      "Bi1QJn47A71vD7Y2L6gT6y"
    """
    if not filepath:
        return None
    pattern = re.compile(r'(?<=\bfile[-_])([^-\s]+)(?=-)', re.IGNORECASE)
    match = pattern.search(filepath)
    if match:
        return match.group(0)
    return None

def find_message_for_file_id(file_id: str, role: str):
    """
    Searches for a message with the specified role whose content contains the file ID.
    Returns the first matching message, or None if not found.
    """
    with get_session() as session:
        # Use ilike for case-insensitive search.
        message = session.query(Message).filter(
            Message.content.ilike(f"%{file_id}%")
        ).filter(
            Message.meta_info["author_role"].astext.ilike(role)
        ).first()
    return message

def update_media_with_message_id(limit: int, role: str):
    updated_count = 0
    processed_count = 0

    # Query all media records with media_type 'image'
    with get_session() as session:
        media_records = session.query(Media).filter(
            Media.media_type == 'image'
        ).all()

    for media in media_records:
        # Skip if already updated.
        if media.meta_info and "source_message_id" in media.meta_info:
            continue

        file_id = extract_file_id_from_filepath(media.file_path)
        if not file_id:
            continue

        msg = find_message_for_file_id(file_id, role)
        processed_count += 1

        if msg:
            # Update media.meta_info with the found message ID.
            if media.meta_info is None:
                media.meta_info = {}
            media.meta_info["source_message_id"] = str(msg.id)
            with get_session() as session:
                session.merge(media)
                session.commit()
            updated_count += 1

        if processed_count >= limit:
            break

    print(f"Processed {processed_count} media records; updated {updated_count} with source_message_id.")

def main():
    parser = argparse.ArgumentParser(
        description="Update media records (images) with a corresponding message ID based on file ID matching."
    )
    parser.add_argument("--limit", type=int, default=100,
                        help="Maximum number of media records to process (default: 100)")
    parser.add_argument("--role", type=str, default="tool",
                        help="Role of messages to match (default: 'tool')")
    args = parser.parse_args()
    update_media_with_message_id(args.limit, args.role)

if __name__ == "__main__":
    main()
