#!/usr/bin/env python3
"""
Non-interactive script to automatically create Media table rows for all files in the archive folder ("chat")
that are referenced in messages. Files that already have a Media row will be skipped.
"""

import re
import os
from pathlib import Path
from carchive.database.session import get_session
from carchive.database.models import Message, Media

def scan_archive_folder(folder_path: str):
    """Recursively scan the folder for files."""
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder {folder_path} does not exist.")
        return []
    return [f for f in folder.rglob("*") if f.is_file()]

def extract_file_id(filename: str):
    """
    Extracts a file ID from the filename.

    For uploaded/generated files, the filename starts with "file-<ID>-".
    For audio files, it starts with "file_<ID>-".
    """
    pattern_dash = re.compile(r"^file-([^-]+)-")
    pattern_underscore = re.compile(r"^file_([^-]+)-")
    m_dash = pattern_dash.match(filename)
    if m_dash:
        return m_dash.group(1)
    m_underscore = pattern_underscore.match(filename)
    if m_underscore:
        return m_underscore.group(1)
    return None

def find_messages_for_file_id(file_id: str):
    """Return all messages whose content references the given file ID (case-insensitive search)."""
    with get_session() as session:
        messages = session.query(Message).filter(Message.content.ilike(f"%{file_id}%")).all()
    return messages

def create_media_row(file_path: str):
    """
    Create a new Media row for the given file path.
    Determine the media_type based on the file extension.
    Returns the new Media object if created, or None if it already exists.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        media_type = "image"
    elif ext in [".wav", ".mp3", ".mp4"]:
        media_type = "audio"  # or "video" as appropriate
    elif ext in [".pdf"]:
        media_type = "pdf"
    else:
        media_type = "other"

    with get_session() as session:
        # Check if a Media row already exists for this file_path
        existing = session.query(Media).filter_by(file_path=file_path).first()
        if existing:
            return None  # Skip creation if it already exists
        new_media = Media(file_path=file_path, media_type=media_type)
        session.add(new_media)
        session.commit()
        session.refresh(new_media)
        return new_media

def main():
    archive_folder = "chat"  # Adjust this if your archive folder is named differently or located elsewhere.
    files = scan_archive_folder(archive_folder)
    print(f"Found {len(files)} files in folder '{archive_folder}'.")

    created_count = 0
    skipped_count = 0

    for file in files:
        file_id = extract_file_id(file.name)
        if not file_id:
            print(f"File '{file.name}' does not have a recognizable file ID; skipping.")
            continue

        msgs = find_messages_for_file_id(file_id)
        if not msgs:
            print(f"No messages reference file ID '{file_id}' (from file '{file.name}'); skipping.")
            continue

        # Check if a Media row for this file already exists
        with get_session() as session:
            exists = session.query(Media).filter_by(file_path=str(file)).first()
        if exists:
            print(f"Media row already exists for file '{file}'; skipping.")
            skipped_count += 1
            continue

        new_media = create_media_row(str(file))
        if new_media:
            print(f"Created media row: {new_media.id} for file '{file}'.")
            created_count += 1
        else:
            print(f"Media row already exists for file '{file}'; skipping.")
            skipped_count += 1

    print(f"\nFinished processing. Created {created_count} new media rows; skipped {skipped_count} files.")

if __name__ == "__main__":
    main()
