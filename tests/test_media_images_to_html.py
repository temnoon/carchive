#!/usr/bin/env python3
# tests/test_media_images_to_html.py
"""
This script queries the media table for image entries and creates an HTML file
that displays up to --limit images. The output HTML file is saved in the specified
output folder with a timestamp in the filename.
"""

import os
import argparse
from datetime import datetime
from carchive.database.session import get_session
from carchive.database.models import Media

def get_image_media(limit: int):
    """Return up to 'limit' Media rows with media_type equal to 'image'."""
    with get_session() as session:
        images = session.query(Media).filter(Media.media_type == 'image').limit(limit).all()
    return images

def render_images_to_html(images, output_folder: str, timestamp_str: str):
    """Generate an HTML file that displays the given images using their file paths."""
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Create a timestamped filename
    output_filename = f"messages_with_images_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    # Build the HTML content
    html_content = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Messages Containing Images</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        .image-entry { margin-bottom: 20px; }
        img { max-width: 100%; height: auto; }
        hr { border: 1px solid #ccc; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Messages Containing Images</h1>
"""
    if not images:
        html_content += "<p>No messages with images found.</p>\n"
    else:
        for media in images:
            # Assume media.file_path is relative (e.g. "chat/file-....jpeg")
            html_content += f"""
    <div class="image-entry">
        <img src="{media.file_path}" alt="Image {media.id}">
        <p>{media.file_path}</p>
    </div>
    <hr>
"""
    html_content += """
</body>
</html>
"""
    # Write the HTML file
    with open(output_path, 'w') as f:
        f.write(html_content)

    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate an HTML file of image media entries from the media table."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of image entries to include")
    parser.add_argument("--output_folder", type=str, default="output", help="Folder to write the HTML file")
    args = parser.parse_args()

    # Create a timestamp string for the filename (e.g. 20250301_154500)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    images = get_image_media(args.limit)
    render_images_to_html(images, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
