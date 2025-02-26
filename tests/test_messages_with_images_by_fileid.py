#!/usr/bin/env python3
"""
This script iterates through the messages table to find messages that have an associated file ID.
The file ID is determined as follows:
  - If the message content contains a substring starting with "file-" or "file_"
    (followed immediately by the file ID and then a hyphen), that file ID is used.
  - Otherwise, if the message metadata (converted to a string) is purely alphanumeric
    and longer than 5 characters, that value is assumed to be the file ID.
For each message with a file ID, the script queries the Media table for image rows (media_type = "image")
whose file_path contains that file ID.
It collects up to --limit messages and then generates an HTML file (saved in the specified output folder
with a timestamp in its filename) that displays each message along with all its associated images.
Usage:
  python tests/test_messages_with_images_by_fileid_only.py --limit 10 --output_folder "output"
"""

import os
import re
import argparse
from datetime import datetime
from carchive.database.session import get_session
from carchive.database.models import Message, Media

def extract_file_id_from_text(text: str):
    """
    Attempts to extract a file ID from text.

    First, look for a pattern where the text contains "file-" or "file_" followed by the ID and then a hyphen.
    For example, from "file-5V0k5hDc2L9NJqQ1QOW36uK5-photo-....jpeg" it will extract "5V0k5hDc2L9NJqQ1QOW36uK5".

    If that pattern is not found, and the entire text is purely alphanumeric and longer than 5 characters,
    assume the text itself is the file ID.
    """
    if not text:
        return None
    # Pattern: lookbehind for "file-" or "file_" and then capture until the next hyphen.
    pattern = re.compile(r'(?<=\bfile[-_])([^-\s]+)(?=-)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(0)
    # Otherwise, if the text is a candidate (entirely alphanumeric and longer than 5 characters), return it.
    candidate = text.strip()
    if re.fullmatch(r'[a-zA-Z0-9]+', candidate) and len(candidate) > 5:
        return candidate
    return None

def extract_file_id(message):
    """
    Extracts a file ID from a Message.
    First tries the message content; if nothing is found, then uses the metadata (converted to a string).
    """
    file_id = None
    if message.content:
        file_id = extract_file_id_from_text(message.content)
    if not file_id and message.meta_info:
        file_id = extract_file_id_from_text(str(message.meta_info))
    return file_id

def get_messages_with_images(limit: int):
    """
    Iterates through all messages.
    For each message, extract a file ID (from content or meta).
    If a file ID is found, query the Media table for rows (with media_type 'image')
    whose file_path contains that file ID.
    Collect up to 'limit' messages (each with one or more associated Media rows)
    and return them as a list of tuples: (message, [Media rows]).
    """
    messages_with_images = []
    with get_session() as session:
        all_messages = session.query(Message).all()

    for msg in all_messages:
        file_id = extract_file_id(msg)
        if not file_id:
            continue  # Skip messages without a file ID.
        with get_session() as session:
            media_matches = session.query(Media).filter(
                Media.media_type == 'image',
                Media.file_path.ilike(f"%{file_id}%")
            ).all()
        if media_matches:
            messages_with_images.append((msg, media_matches))
        if len(messages_with_images) >= limit:
            break

    return messages_with_images

def generate_html_for_messages(msg_media_pairs, output_folder: str, timestamp_str: str):
    """
    Generates an HTML file that displays each message's content and all its associated images.
    Each image is rendered using an <img> tag with an absolute file URL.
    """
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"messages_with_images_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Messages with Images</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .message-entry { margin-bottom: 30px; }
        .message-entry img { max-width: 100%; height: auto; margin-right: 10px; }
        hr { border: 1px solid #ccc; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Messages with Images</h1>
"""
    if not msg_media_pairs:
        html_content += "<p>No messages with images found.</p>\n"
    else:
        for msg, media_list in msg_media_pairs:
            file_id = extract_file_id(msg) or "N/A"
            html_content += f"""<div class="message-entry">
    <h2>Message ID: {msg.id}</h2>
    <p><strong>Content:</strong> {msg.content}</p>
    <p><strong>Extracted File ID:</strong> {file_id}</p>
    <div class="images">
"""
            for media in media_list:
                abs_path = os.path.abspath(media.file_path)
                file_url = "file://" + abs_path
                html_content += f"""        <img src="{file_url}" alt="Image {media.id}">
        <p><small>{abs_path}</small></p>
"""
            html_content += "    </div>\n    <hr>\n</div>\n"
    html_content += """
</body>
</html>
"""
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Search messages for a file ID (from content or meta) and render messages with images into an HTML file."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of messages to process (default: 10)")
    parser.add_argument("--output_folder", type=str, default="output", help="Folder for the output HTML file (default: 'output')")
    args = parser.parse_args()

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    msg_media_pairs = get_messages_with_images(args.limit)
    generate_html_for_messages(msg_media_pairs, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
