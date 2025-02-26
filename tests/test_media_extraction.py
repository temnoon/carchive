#!/usr/bin/env python3
# tests/test_media_extraction.py
"""
Test script to verify how media file IDs are stored in messages and to process the archive
to create media table rows for files referenced in messages.

This script:
  1. Queries messages from the database and prints out any media file ID patterns found
     in the message content or metadata.
  2. Scans the specified archive folder (e.g. "chat/") for files.
  3. For each file, extracts its file ID (using the naming conventions described) and finds
     messages that reference that ID.
  4. Prompts the user to create a media table row for that file.
"""

import re
from pathlib import Path
from carchive.database.session import get_session
from carchive.database.models import Message, Media

# --- 1. Check messages for media references ---
def inspect_message_media_references():
    print("=== Inspecting Messages for Media References ===\n")
    with get_session() as session:
        messages = session.query(Message).all()
        for msg in messages:
            print(f"Message ID: {msg.id}")
            if msg.content:
                # Pattern for uploaded / generated files: "file-<ID>-"
                pattern_dash = re.compile(r"file-([^-]+)-")
                # Pattern for audio files: "file_<ID>-"
                pattern_underscore = re.compile(r"file_([^-]+)-")
                dash_matches = pattern_dash.findall(msg.content)
                underscore_matches = pattern_underscore.findall(msg.content)
                if dash_matches:
                    print("  Uploaded/Generated file IDs in content:", dash_matches)
                if underscore_matches:
                    print("  Audio file IDs in content:", underscore_matches)
            if msg.meta_info and isinstance(msg.meta_info, dict):
                media_refs = msg.meta_info.get("media_references")
                if media_refs:
                    print("  Media references in meta_info:", media_refs)
            print("-" * 40)

# --- 2. Scan the archive folder for files ---
def scan_archive(folder_path: str):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Folder {folder_path} does not exist.")
        return []
    return [f for f in folder.rglob("*") if f.is_file()]

# --- 3. Extract file ID from a given file name ---
def extract_file_id(filename: str):
    # For uploaded and generated files (e.g., file-H3IR6iFnPYBfpO9Zj6hQ2edX-photo-...jpeg)
    pattern_dash = re.compile(r"^file-([^-]+)-")
    # For audio files (e.g., file_1aada74527ac30021aa226664ce50cf0c753012b9aa7bfa60cb8b7f32a6bb1c427d63a0a52aab272d47753ccba02f6d9-54f53517-0087-4c3a-9e33-38798baa1d25.wav)
    pattern_underscore = re.compile(r"^file_([^-]+)-")
    m_dash = pattern_dash.match(filename)
    if m_dash:
        return m_dash.group(1)
    m_underscore = pattern_underscore.match(filename)
    if m_underscore:
        return m_underscore.group(1)
    return None

# --- 4. Find messages that reference a given file ID ---
def find_messages_for_file_id(file_id: str):
    with get_session() as session:
        return session.query(Message).filter(Message.content.ilike(f"%{file_id}%")).all()

# --- 5. Create a Media table row for a file ---
def create_media_row_for_file(file_path: str):
    import os
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        media_type = "image"
    elif ext in [".wav", ".mp3", ".mp4"]:
        media_type = "audio"  # (or "video" if you prefer)
    elif ext in [".pdf"]:
        media_type = "pdf"
    else:
        media_type = "other"
    with get_session() as session:
        existing = session.query(Media).filter_by(file_path=file_path).first()
        if existing:
            print(f"Media row already exists for {file_path} (ID: {existing.id})")
            return existing
        new_media = Media(file_path=file_path, media_type=media_type)
        session.add(new_media)
        session.commit()
        session.refresh(new_media)
        print(f"Created media row: {new_media.id} for file {file_path}")
        return new_media

# --- Main ---
def main():
    # A. Inspect messages to see how file IDs appear
    inspect_message_media_references()

    # B. Scan the archive folder (adjust the folder path as needed)
    archive_folder = "chat"  # or the appropriate path to your extracted archive folder
    files = scan_archive(archive_folder)
    print(f"\nFound {len(files)} files in folder '{archive_folder}'.")
    for f in files:
        print(f"  {f}")

    # C. For each file, try to extract the file ID and check for referencing messages.
    for file in files:
        file_id = extract_file_id(file.name)
        if file_id:
            print(f"\nFile: {file.name}")
            print(f"  Extracted file ID: {file_id}")
            msgs = find_messages_for_file_id(file_id)
            if msgs:
                print(f"  Found {len(msgs)} message(s) referencing file ID {file_id}:")
                for m in msgs:
                    print(f"    - Message ID: {m.id}")
                answer = input(f"  Create a media row for file '{file}'? (y/n): ")
                if answer.strip().lower() == "y":
                    create_media_row_for_file(str(file))
            else:
                print(f"  No messages reference file ID {file_id}.")
        else:
            print(f"\nFile: {file.name} does not match the expected naming pattern.")

if __name__ == "__main__":
    main()
