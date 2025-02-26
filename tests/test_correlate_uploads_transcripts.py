#!/usr/bin/env python3
"""
Correlate uploaded images (in user messages) with subsequent assistant transcript messages.

For each conversation (optionally restricted by --conversation_id and limited by --limit),
this script:
  1. Queries for the conversation and its messages (sorted by created_at).
  2. Identifies user messages (author_role=="user") that contain a file reference.
     The file reference is assumed to be the substring immediately after "file-" or "file_"
     and ending at the next hyphen.
  3. For each such user message, it looks up a Media record (with media_type=="image")
     whose file_path contains that file ID.
  4. It then collects subsequent assistant messages (author_role=="assistant")
     in the same conversation.
  5. Finally, it generates an HTML file that displays the conversation along with the correlated entries.

Usage:
  python tests/test_correlate_uploads_transcripts.py --limit 10 --output_folder "output"
  (Optionally add --conversation_id <conv_id> to restrict to a specific conversation.)
"""

import os
import re
import argparse
from datetime import datetime
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, Media

def get_messages_for_conversation(conv_id):
    """Query messages for a given conversation ID, sorted by created_at ascending."""
    with get_session() as session:
        messages = session.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return messages

def get_message_role(msg):
    """Return the lower-case role from the message's metadata (if available)."""
    if msg.meta_info and isinstance(msg.meta_info, dict):
        return msg.meta_info.get("author_role", "").lower()
    return ""

def extract_file_id(text: str):
    """
    Extract the file id from text.
    The file id is assumed to be the string immediately following "file-" or "file_"
    and ending at the next hyphen.
    For example, from "file-5V0k5hDc2L9NJqQ1QOW36uK5-photo-..." it extracts "5V0k5hDc2L9NJqQ1QOW36uK5".
    """
    if not text:
        return None
    pattern = re.compile(r'(?<=\bfile[-_])([^-\s]+)(?=-)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        return match.group(0)
    return None

def correlate_conversation(conv):
    """
    For a given conversation, retrieve its messages (sorted by created_at).
    Then, for each user message (author_role=="user") that contains a file reference,
    extract the file id and look up a Media record (with media_type=="image") whose file_path
    contains that file id. Then, collect all subsequent assistant messages in that conversation.
    Returns a list of tuples: (user_message, media_record or None, [assistant_messages]).
    """
    messages = get_messages_for_conversation(conv.id)
    correlations = []
    for i, msg in enumerate(messages):
        if get_message_role(msg) != "user":
            continue
        file_id = extract_file_id(msg.content)
        if not file_id:
            continue
        with get_session() as session:
            media_record = session.query(Media).filter(
                Media.media_type == 'image',
                Media.file_path.ilike(f"%{file_id}%")
            ).first()
        # Collect subsequent assistant messages
        assistant_msgs = [m for m in messages[i+1:] if get_message_role(m) == "assistant"]
        correlations.append((msg, media_record, assistant_msgs))
    return correlations

def get_conversations(limit, conv_id=None):
    """
    Query the Conversation table.
    Optionally filter by conv_id; otherwise return up to limit conversations ordered by created_at descending.
    """
    with get_session() as session:
        query = session.query(Conversation)
        if conv_id:
            query = query.filter(Conversation.id == conv_id)
        query = query.order_by(Conversation.created_at.desc()).limit(limit)
        convs = query.all()
    return convs

def generate_html(correlations_by_conv, output_folder, timestamp_str):
    """
    Generate an HTML file that displays each conversation's correlations.
    For each conversation, display:
      - Conversation ID (and title if available)
      - For each correlated entry: display the user message content, the associated image (if found),
        and the subsequent assistant transcript messages.
    """
    os.makedirs(output_folder, exist_ok=True)
    output_filename = f"upload_transcript_correlation_{timestamp_str}.html"
    output_path = os.path.join(output_folder, output_filename)

    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Upload & Transcript Correlation</title>
  <style>
    body { font-family: sans-serif; margin: 20px; }
    .conversation { border: 2px solid #333; padding: 10px; margin-bottom: 20px; }
    .entry { border: 1px solid #ccc; padding: 10px; margin: 10px 0; }
    .entry img { max-width: 100%; height: auto; display: block; margin: 10px 0; }
    hr { border: 1px solid #ddd; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>Upload & Transcript Correlation</h1>
"""
    if not correlations_by_conv:
        html += "<p>No conversations with correlated uploads and transcripts found.</p>\n"
    else:
        for conv, correlations in correlations_by_conv:
            html += f"<div class='conversation'><h2>Conversation ID: {conv.id}</h2>"
            if conv.title:
                html += f"<p><strong>Title:</strong> {conv.title}</p>"
            for user_msg, media_record, assistant_msgs in correlations:
                html += "<div class='entry'>"
                html += f"<h3>User Message ID: {user_msg.id}</h3>"
                html += f"<p><strong>Content:</strong> {user_msg.content}</p>"
                if media_record:
                    abs_path = os.path.abspath(media_record.file_path)
                    file_url = "file://" + abs_path
                    html += f"<img src='{file_url}' alt='Uploaded Image'>"
                    html += f"<p><small>Media File: {media_record.file_path}</small></p>"
                else:
                    html += "<p><em>No associated media record found.</em></p>"
                if assistant_msgs:
                    html += "<h4>Assistant Transcript(s):</h4>"
                    for asm in assistant_msgs:
                        html += f"<p><strong>Message ID: {asm.id}</strong>: {asm.content}</p>"
                else:
                    html += "<p><em>No assistant transcript messages found after this upload.</em></p>"
                html += "</div>"  # end entry
            html += "</div>"  # end conversation
    html += "</body></html>"

    with open(output_path, "w") as f:
        f.write(html)
    print(f"HTML file created: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Correlate uploaded images (in user messages) with subsequent assistant transcript messages."
    )
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of conversations to process (default: 10)")
    parser.add_argument("--conversation_id", type=str, default=None,
                        help="Specific conversation ID to process")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Output folder for the HTML file (default: 'output')")
    args = parser.parse_args()

    convs = get_conversations(args.limit, args.conversation_id)
    correlations_by_conv = []
    for conv in convs:
        correlations = correlate_conversation(conv)
        if correlations:
            correlations_by_conv.append((conv, correlations))
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    generate_html(correlations_by_conv, args.output_folder, timestamp_str)

if __name__ == "__main__":
    main()
