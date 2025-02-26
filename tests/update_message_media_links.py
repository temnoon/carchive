#!/usr/bin/env python3
"""
This script iterates over messages that contain a file reference in their content,
extracts the file id (the string immediately after "file-service://file-"),
and then looks up a corresponding Media record (where media_type = "image")
whose file_path contains that file id. If found, it updates the message's
media_id field to link the message to that media record.

Usage:
    python tests/update_message_media_links.py --limit 100
"""

import re
import argparse
from carchive.database.session import get_session
from carchive.database.models import Message, Media

def extract_file_id_from_content(content: str):
    """
    Extract the file id from the content.

    This function looks for a pattern like:
      "file-service://file-<file_id>"
    and returns the <file_id> (which should be an alphanumeric string).
    """
    if not content:
        return None
    # This regex looks for "file-service://file-" followed by one or more alphanumeric characters.
    pattern = re.compile(r'file-service://file-([A-Za-z0-9]+)', re.IGNORECASE)
    match = pattern.search(content)
    if match:
        return match.group(1)
    return None

def update_message_media_links(limit: int):
    updated_count = 0
    no_match_count = 0
    processed_count = 0

    # Query messages that do have a file reference and are not yet linked.
    with get_session() as session:
        messages = session.query(Message).filter(
            Message.media_id == None,
            Message.content.ilike('%file-service://file-%')
        ).limit(limit).all()

    for msg in messages:
        processed_count += 1
        file_id = extract_file_id_from_content(msg.content)
        if not file_id:
            continue  # Skip if we couldn't extract a file id

        # Look up a media record whose file_path contains the file id.
        with get_session() as session:
            media_record = session.query(Media).filter(
                Media.media_type == 'image',
                Media.file_path.ilike(f"%{file_id}%")
            ).first()

            if media_record:
                # Update the message's media_id to link it with the found media.
                msg.media_id = media_record.id
                session.merge(msg)
                session.commit()
                updated_count += 1
            else:
                no_match_count += 1

    print(f"Processed {processed_count} messages.")
    print(f"Updated {updated_count} messages with media links.")
    print(f"{no_match_count} messages did not have a matching media record.")

def main():
    parser = argparse.ArgumentParser(
        description="Link messages with file references to their corresponding media records."
    )
    parser.add_argument("--limit", type=int, default=100,
                        help="Number of messages to process (default: 100)")
    args = parser.parse_args()
    update_message_media_links(args.limit)

if __name__ == "__main__":
    main()
