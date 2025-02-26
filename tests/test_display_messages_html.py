#!/usr/bin/env python3
"""
This script queries the messages table and displays messages (in reverse order by creation date)
with optional search filters for the message content and metadata.
It generates an HTML file in a specified output folder (default "output") with a timestamp in its filename.
For each message, it displays:
  - Message ID
  - Content
  - Metadata (rendered in a human-readable YAML format)
Usage:
  python tests/test_display_messages_html.py --limit 10 --content_search "foo" --meta_search "bar" --output_folder "output"
"""

import os
import argparse
from datetime import datetime
import yaml  # requires PyYAML; install with pip if needed
from carchive.database.session import get_session
from carchive.database.models import Message
from sqlalchemy import cast
from sqlalchemy.types import Text

def get_filtered_messages(content_search: str, meta_search: str, limit: int):
    """
    Query the messages table for messages that match the search criteria.
    - If content_search is provided, only messages whose content contains that text (case-insensitive) are returned.
    - If meta_search is provided, only messages whose metadata (cast to text) contains that text are returned.
    The results are ordered in reverse order by created_at (most recent first).
    """
    with get_session() as session:
        query = session.query(Message)
        if content_search:
            query = query.filter(Message.content.ilike(f"%{content_search}%"))
        if meta_search:
            # Cast the JSON meta_info to text for a simple search
            query = query.filter(cast(Message.meta_info, Text).ilike(f"%{meta_search}%"))
        query = query.order_by(Message.created_at.desc())
        messages = query.limit(limit).all()
    return messages

def generate_html_for_messages(messages, output_folder: str, timestamp_str: str):
    """
    Generate an HTML file that displays each message's ID, content, and metadata (in YAML format).
    """
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"messages_display_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Displayed Messages</title>
  <style>
    body { font-family: sans-serif; margin: 20px; }
    .message-entry { margin-bottom: 30px; padding: 10px; border: 1px solid #ccc; }
    pre { background: #f8f8f8; padding: 10px; }
    hr { border: 1px solid #ddd; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>Displayed Messages</h1>
"""
    if not messages:
        html_content += "<p>No messages found matching the criteria.</p>\n"
    else:
        for msg in messages:
            # Use PyYAML to dump the meta_info in a human-readable format.
            meta_yaml = yaml.dump(msg.meta_info, default_flow_style=False, sort_keys=False) if msg.meta_info else "None"
            html_content += f"""<div class="message-entry">
  <h2>Message ID: {msg.id}</h2>
  <p><strong>Content:</strong> {msg.content}</p>
  <pre><strong>Metadata:</strong>\n{meta_yaml}</pre>
  <hr>
</div>
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
        description="Display messages (reverse order) with optional content and metadata search filters."
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of messages to display (default: 10)")
    parser.add_argument("--content_search", type=str, default="", help="Search string for message content (case-insensitive)")
    parser.add_argument("--meta_search", type=str, default="", help="Search string for metadata (case-insensitive)")
    parser.add_argument("--output_folder", type=str, default="output", help="Output folder for the HTML file (default: 'output')")
    args = parser.parse_args()

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    messages = get_filtered_messages(args.content_search, args.meta_search, args.limit)
    generate_html_for_messages(messages, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
