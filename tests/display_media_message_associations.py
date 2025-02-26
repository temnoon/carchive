#!/usr/bin/env python3
"""
Display Media–Message Associations

This script finds media records (with media_type=="image") and attempts to
locate their associated messages. It then groups these associations by conversation
(based on the associated message’s conversation_id) and generates one HTML file per
conversation. Each HTML file displays:
  - The conversation ID (and title if available)
  - For each media record:
      - The image (rendered using an absolute file URL)
      - The media record metadata (rendered in YAML style, if available)
      - The associated message’s details (ID, content, metadata) with HTML escaping.

Usage:
    python tests/display_media_message_associations.py --limit 100 --output_folder "output"

If more than one conversation is processed, the HTML files will be placed in a
timestamp‐named subfolder.
"""

import os
import argparse
import html
from datetime import datetime
import yaml  # Requires PyYAML (pip install PyYAML)
from collections import defaultdict

from carchive.database.session import get_session
from carchive.database.models import Media, Message, Conversation

def get_associated_message(media):
    """
    For a given media record, try to retrieve its associated message.
    First, if media has a meta_info attribute containing "source_message_id", use that.
    Otherwise, try to find a Message where Message.media_id equals media.id.
    Returns the associated Message (or None if not found).
    """
    media_meta = getattr(media, "meta_info", {})
    message = None
    if isinstance(media_meta, dict) and "source_message_id" in media_meta:
        source_msg_id = media_meta["source_message_id"]
        with get_session() as session:
            # Using Session.get() instead of Query.get() for SQLAlchemy 2.0 style.
            message = session.get(Message, source_msg_id)
    if not message:
        with get_session() as session:
            message = session.query(Message).filter(Message.media_id == media.id).first()
    return message

def query_linked_media(limit):
    """
    Query the Media table for image records and for each record attempt to find an
    associated message (using the source_message_id in meta_info if available, or by messages with media_id == media.id).
    Returns a list of tuples: (media, associated_message).
    """
    linked = []
    with get_session() as session:
        media_records = session.query(Media).filter(Media.media_type == 'image').limit(limit).all()
    for media in media_records:
        msg = get_associated_message(media)
        if msg:
            linked.append((media, msg))
    return linked

def group_by_conversation(linked_pairs):
    """
    Group the media-message pairs by conversation.
    Uses the conversation_id from the associated message.
    Returns a dict mapping conversation_id to a list of (media, message) tuples.
    """
    groups = defaultdict(list)
    for media, msg in linked_pairs:
        conv_id = msg.conversation_id  # assume this is set
        groups[conv_id].append((media, msg))
    return groups

def get_conversation_info(conv_id):
    """Retrieve a Conversation record by its id."""
    with get_session() as session:
        # Use session.get() if possible
        conv = session.get(Conversation, conv_id)
    return conv

def generate_html_for_conversation(conv, media_message_pairs, output_folder, timestamp_str):
    """
    Generate an HTML file for a single conversation.
    The file displays the conversation ID (and title, if available) along with each media record,
    its metadata (rendered in YAML), and the details of the associated message (with HTML-escaped text).
    """
    # Escape conv.id in the title
    conv_id_str = html.escape(str(conv.id))
    filename = f"conversation_{conv_id_str}_{timestamp_str}.html"
    output_path = os.path.join(output_folder, filename)

    # Note: double all curly braces in the style block for literal curly braces.
    html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Media–Message Associations for Conversation {conv_id}</title>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .media-entry {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; }}
    .media-entry img {{ max-width: 100%; height: auto; display: block; margin-bottom: 10px; }}
    pre {{ background: #f8f8f8; padding: 10px; }}
    hr {{ border: 1px solid #ddd; margin: 20px 0; }}
  </style>
</head>
<body>
  <h1>Conversation ID: {conv_id}</h1>
""".format(conv_id=conv_id_str)
    if hasattr(conv, "title") and conv.title:
        html_content += "<h2>Title: {}</h2>\n".format(html.escape(conv.title))

    for media, msg in media_message_pairs:
        abs_path = os.path.abspath(media.file_path)
        file_url = "file://" + abs_path
        media_meta = {
            "id": str(media.id),
            "file_path": media.file_path,
            "media_type": media.media_type,
            "created_at": str(media.created_at)
        }
        media_yaml = yaml.dump(media_meta, default_flow_style=False, sort_keys=False)
        msg_content = html.escape(msg.content) if msg.content else ""
        msg_meta = getattr(msg, "meta_info", {})
        msg_yaml = yaml.dump(msg_meta, default_flow_style=False, sort_keys=False)
        html_content += f"""<div class="media-entry">
  <h3>Media ID: {html.escape(str(media.id))}</h3>
  <img src="{file_url}" alt="Media Image {html.escape(str(media.id))}">
  <pre>{html.escape(media_yaml)}</pre>
  <h4>Associated Message</h4>
  <p><strong>Message ID:</strong> {html.escape(str(msg.id))}</p>
  <p><strong>Content:</strong> {msg_content}</p>
  <pre>{html.escape(msg_yaml)}</pre>
  <hr>
</div>
"""
    html_content += """
</body>
</html>
"""
    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"HTML file created for conversation {conv.id}: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Display associations between media (images) and messages in separate HTML files per conversation."
    )
    parser.add_argument("--limit", type=int, default=100,
                        help="Number of media records to process (default: 100)")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Folder to store the output HTML files (default: 'output')")
    args = parser.parse_args()

    linked_pairs = query_linked_media(args.limit)
    if not linked_pairs:
        print("No linked media-message associations found.")
        return

    groups = group_by_conversation(linked_pairs)
    if not groups:
        print("No conversation associations found.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(args.output_folder, f"run_{timestamp_str}")
    os.makedirs(run_folder, exist_ok=True)

    for conv_id, pairs in groups.items():
        conv = get_conversation_info(conv_id)
        if conv:
            generate_html_for_conversation(conv, pairs, run_folder, timestamp_str)
        else:
            print(f"Conversation {conv_id} not found.")

if __name__ == "__main__":
    main()
