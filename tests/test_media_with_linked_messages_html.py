#!/usr/bin/env python3
"""
This script queries the media table for image records (media_type = "image") and for each media record
finds all messages that reference it (i.e. messages with media_id matching the media record's id).
It then generates an HTML file (saved in the specified output folder with a timestamped filename)
that displays:
  - The image (using an absolute file URL)
  - The media record metadata (rendered in YAML-style)
  - The linked messages (showing message id and content)
Usage:
  python tests/test_media_with_linked_messages_html.py --limit 10 --output_folder "output"
"""

import os
import argparse
from datetime import datetime
import yaml  # Requires PyYAML; install with: pip install PyYAML

from carchive.database.session import get_session
from carchive.database.models import Media, Message

def get_media_with_messages(limit: int):
    """
    Query the Media table for image records (media_type = 'image') in reverse creation order,
    and for each media record, fetch all messages that reference it.
    Returns a list of tuples: (media, [message, message, ...])
    """
    results = []
    with get_session() as session:
        # Order by created_at descending (most recent first)
        media_records = session.query(Media).filter(Media.media_type == 'image') \
                                          .order_by(Media.created_at.desc()) \
                                          .limit(limit).all()
    for media in media_records:
        with get_session() as session:
            messages = session.query(Message).filter(Message.media_id == media.id).all()
        results.append((media, messages))
    return results

def generate_html(media_messages, output_folder: str, timestamp_str: str):
    """
    Generate an HTML file that displays each media record along with its associated messages.
    For each media record, the image is rendered using an <img> tag with an absolute file URL.
    The media metadata is rendered in a YAML-style block.
    """
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"media_with_messages_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Media with Linked Messages</title>
  <style>
    body { font-family: sans-serif; margin: 20px; }
    .media-entry { margin-bottom: 40px; padding: 10px; border: 1px solid #ccc; }
    .media-entry img { max-width: 100%; height: auto; display: block; margin-bottom: 10px; }
    pre { background: #f8f8f8; padding: 10px; }
    hr { border: 1px solid #ddd; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>Media with Linked Messages</h1>
"""
    if not media_messages:
        html_content += "<p>No media records found.</p>\n"
    else:
        for media, messages in media_messages:
            # Get the absolute path for the media file and form a file:// URL
            abs_path = os.path.abspath(media.file_path)
            file_url = "file://" + abs_path
            # Dump the media metadata in YAML format for readability
            media_meta_yaml = yaml.dump({
                "id": str(media.id),
                "file_path": media.file_path,
                "media_type": media.media_type,
                "created_at": str(media.created_at)
            }, default_flow_style=False, sort_keys=False)
            html_content += f"""<div class="media-entry">
  <h2>Media ID: {media.id}</h2>
  <img src="{file_url}" alt="Media Image {media.id}">
  <pre>{media_meta_yaml}</pre>
  <h3>Linked Messages ({len(messages)})</h3>
"""
            if not messages:
                html_content += "<p>No linked messages.</p>\n"
            else:
                for msg in messages:
                    # For each linked message, display its id and content.
                    html_content += f"""<div class="message-entry">
    <p><strong>Message ID:</strong> {msg.id}</p>
    <p><strong>Content:</strong> {msg.content}</p>
    <hr>
  </div>
"""
            html_content += "</div>\n<hr>\n"
    html_content += """
</body>
</html>
"""
    with open(output_path, 'w') as f:
        f.write(html_content)
    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Display media records (images) along with the messages linked to them in an HTML file."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of media records to display (default: 10)")
    parser.add_argument("--output_folder", type=str, default="output", help="Folder for the output HTML file (default: 'output')")
    args = parser.parse_args()

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    media_messages = get_media_with_messages(args.limit)
    generate_html(media_messages, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
