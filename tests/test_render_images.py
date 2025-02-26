#!/usr/bin/env python3
"""
This script queries the media table for image entries (media_type = "image"),
takes a --limit parameter, and writes an HTML file (saved in a specified output folder,
defaulting to "output") whose filename includes a timestamp.
Each image is rendered with an <img> tag using its relative file path.
"""

import os
import argparse
from datetime import datetime
from carchive.database.session import get_session
from carchive.database.models import Media

def get_image_media(limit: int):
    """
    Return up to 'limit' rows from the Media table where media_type is 'image'.
    """
    with get_session() as session:
        images = session.query(Media).filter(Media.media_type == 'image').limit(limit).all()
    return images

def generate_html(images, output_folder: str, timestamp_str: str):
    """
    Generate an HTML file that displays the given images using <img> tags.
    The file is saved in the output_folder with the timestamp in its filename.
    """
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
        .image-entry img { max-width: 100%; height: auto; }
        hr { border: 1px solid #ccc; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Messages Containing Images</h1>
"""
    if not images:
        html_content += "<p>No messages with images found.</p>\n"
    else:
        for image in images:
            # Render each image entry with an <img> tag.
            # It assumes that the file_path stored is relative (e.g. "chat/file-...jpeg")
            html_content += f"""
    <div class="image-entry">
        <h2>Image {image.id}</h2>
        <img src="{image.file_path}" alt="Image {image.id}">
        <p>File path: {image.file_path}</p>
    </div>
    <hr>
"""
    html_content += """
</body>
</html>
"""
    # Write the HTML file to disk
    with open(output_path, 'w') as file:
        file.write(html_content)

    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Render a limited number of image media entries from the media table into an HTML file."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of image entries to render (default: 10)")
    parser.add_argument("--output_folder", type=str, default="output", help="Output folder for the HTML file (default: 'output')")
    args = parser.parse_args()

    # Create a timestamp string for the filename (e.g. 20250301_154500)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    images = get_image_media(args.limit)
    generate_html(images, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
