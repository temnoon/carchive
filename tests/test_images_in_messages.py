#!/usr/bin/env python3
# tests/test_images_in_messages.py
import os
import argparse
from carchive.database.session import get_session
from carchive.database.models import Message, Media

def find_messages_with_images(search_text: str, limit: int, output_folder: str):
    """
    Find messages containing images and filter by search text in the message content.
    """
    with get_session() as session:
        # Query messages that reference images in the media table and filter by search text
        query = (
            session.query(Message)
            .join(Media, Media.id == Message.media_id)  # Join on media table
            .filter(Media.media_type == 'image')  # Only include images
        )

        if search_text:
            query = query.filter(Message.content.ilike(f'%{search_text}%'))  # Apply content search text filter

        # Limit the number of messages
        messages_with_images = query.limit(limit).all()

    return messages_with_images

def render_message_images_to_html(messages, output_folder):
    """
    Render all messages with image media into an HTML file in the output folder.
    """
    # Make sure the output folder exists
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Define the HTML file path
    output_file = os.path.join(output_folder, 'messages_with_images.html')

    # Start building the HTML content
    html_content = """
    <html>
    <head>
        <title>Messages with Images</title>
    </head>
    <body>
        <h1>Messages Containing Images</h1>
    """

    if not messages:
        html_content += "<p>No messages with images found.</p>"
    else:
        # Loop through the messages and create HTML for each message
        for message in messages:
            image_media = message.media
            html_content += f"""
            <div>
                <h2>Message ID: {message.id}</h2>
                <p><strong>Content:</strong> {message.content}</p>
                <img src="chat/{image_media.file_path}" alt="Image {message.id}" style="max-width: 100%;"/>
                <p><small>File Path: {image_media.file_path}</small></p>
            </div>
            <hr />
            """

    # Closing HTML tags
    html_content += """
    </body>
    </html>
    """

    # Write the content to the HTML file
    with open(output_file, 'w') as file:
        file.write(html_content)

    print(f"HTML file created at: {output_file}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Search messages with images and generate HTML.")
    parser.add_argument('--search', type=str, default='', help="Search text for message content")
    parser.add_argument('--limit', type=int, default=10, help="Limit the number of messages to return")
    parser.add_argument('--output_folder', type=str, default='output', help="Output folder for HTML file")

    args = parser.parse_args()

    # Fetch messages with images based on search criteria
    messages = find_messages_with_images(args.search, args.limit, args.output_folder)

    # Render the results into an HTML file
    render_message_images_to_html(messages, args.output_folder)

if __name__ == "__main__":
    main()
