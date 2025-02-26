#!/usr/bin/env python3
"""
This script searches for messages that contain a specified search string (case-insensitive)
in their content. For each message found, it extracts an image filename using a regex
(e.g. filenames starting with "file-" or "file_" and ending with jpg/jpeg/png/webp) and then
looks up a corresponding media row in the media table.
It then generates an HTML file (saved in the specified output folder with a timestamped filename)
that renders each message’s content along with its image.
Usage:
    python tests/test_search_messages_images_to_html.py --search "notebook" --limit 10 --output_folder "output"
"""

import os
import re
import argparse
from datetime import datetime
from carchive.database.session import get_session
from carchive.database.models import Message, Media

def extract_image_filename(text: str):
    """
    Extracts an image filename from the given text.

    The regex looks for filenames that start with "file-" or "file_"
    and end with one of the extensions: jpg, jpeg, png, or webp.
    Returns the first matching filename (if any), or None.
    """
    # This pattern matches filenames like:
    #   file-5V0k5hDc2L9NJqQ1QOW36uK5-photo-7B733798-5709-4D5E-B9AB-35A484D8D311-2-3.jpeg
    #   file_1aada74527ac30021aa226664ce50cf0...jpg
    pattern = re.compile(r'(file[-_][\w\-\s]+?\.(?:jpg|jpeg|png|webp))', re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        return matches[0]
    return None

def get_messages_with_image_by_search(search_text: str, limit: int):
    """
    Queries the Message table for messages whose content contains the given search string,
    then for each message extracts an image filename and looks up a matching Media row.
    Returns a list of tuples: (message, media)
    """
    with get_session() as session:
        # Get messages where the content contains the search text (case-insensitive)
        messages = session.query(Message).filter(Message.content.ilike(f'%{search_text}%')).limit(limit).all()

    result = []
    for msg in messages:
        # Extract an image filename from the message content.
        filename = extract_image_filename(msg.content or "")
        if filename:
            # Look up a Media row whose file_path ends with the extracted filename.
            with get_session() as session:
                media = session.query(Media).filter(Media.media_type == 'image') \
                            .filter(Media.file_path.ilike(f'%{filename}')).first()
            if media:
                result.append((msg, media))
    return result

def generate_html_for_messages(msg_media_pairs, output_folder: str, timestamp_str: str):
    """
    Generates an HTML file that displays each message's content and its associated image.
    The image is rendered using an <img> tag with a full absolute URL (using file://).
    """
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"search_messages_with_images_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Messages with Images</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .message-entry { margin-bottom: 30px; }
        .message-entry img { max-width: 100%; height: auto; }
        hr { border: 1px solid #ccc; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Messages with Images</h1>
"""
    if not msg_media_pairs:
        html_content += "<p>No messages found matching the search criteria.</p>\n"
    else:
        for msg, media in msg_media_pairs:
            # Compute the absolute file path for the media file.
            abs_path = os.path.abspath(media.file_path)
            file_url = "file://" + abs_path
            html_content += f"""
    <div class="message-entry">
        <h2>Message ID: {msg.id}</h2>
        <p><strong>Content:</strong> {msg.content}</p>
        <img src="{file_url}" alt="Image for Message {msg.id}">
        <p><small>Image Path: {abs_path}</small></p>
    </div>
    <hr>
"""
    html_content += """
</body>
</html>
"""
    with open(output_path, 'w') as f:
        f.write(html_content)

    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Search for messages containing a specified text and an image reference, and render them to an HTML file."
    )
    parser.add_argument("--search", type=str, required=True,
                        help="Search string (case-insensitive) in message content")
    parser.add_argument("--limit", type=int, default=10,
                        help="Limit the number of messages to search (default: 10)")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Output folder for the HTML file (default: 'output')")
    args = parser.parse_args()

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    msg_media_pairs = get_messages_with_image_by_search(args.search, args.limit)
    generate_html_for_messages(msg_media_pairs, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
