#!/usr/bin/env python3
"""
Correlate User Prompts with Uploaded Images to Assistant Transcript Responses

For each conversation (optionally filtered by conversation ID, and limited by --limit),
this script:
  1. Retrieves messages sorted by creation time.
  2. Identifies a user prompt message (where meta_info contains a non-empty "attachments" list).
  3. For each such user prompt, it collects the subsequent assistant (or tool) messages as the transcript block.
  4. It generates one HTML file per conversation that displays:
       - The conversation ID (and title, if available).
       - For each correlated block:
            • The user prompt message details (ID and HTML-escaped content).
            • Rendered images from its attachments. (Each attachment is rendered as an <img> tag.
              The file path is assumed to be constructed as "chat/file-<att_id>-<att_name>".)
            • The associated assistant transcript messages (with ID, HTML-escaped content, and YAML-formatted metadata).

Usage:
  python tests/correlate_user_prompt_and_assistant_transcript.py --limit 10 --output_folder "output"
  (Optionally, add --conversation_id <conv_id> to process only one conversation.)
"""

import os
import argparse
import html
import yaml  # Requires PyYAML (pip install PyYAML)
from datetime import datetime

from carchive.database.session import get_session
from carchive.database.models import Conversation, Message

def get_conversations(limit, conv_id=None):
    """Retrieve conversations (ordered by created_at descending)."""
    with get_session() as session:
        query = session.query(Conversation)
        if conv_id:
            query = query.filter(Conversation.id == conv_id)
        query = query.order_by(Conversation.created_at.desc()).limit(limit)
        convs = query.all()
    return convs

def get_messages_for_conversation(conv_id):
    """Retrieve messages for a conversation, sorted by created_at ascending."""
    with get_session() as session:
        msgs = session.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return msgs

def correlate_prompt_and_transcript(messages):
    """
    Given a list of messages (sorted by created_at) from one conversation,
    find user messages that include uploaded images (detected via a non-empty "attachments" list in meta_info)
    and then group with the following assistant messages (or tool messages) as the transcript block.

    Returns a list of tuples: (user_message, [assistant_message, ...]).
    """
    correlations = []
    n = len(messages)
    i = 0
    while i < n:
        msg = messages[i]
        role = ""
        if msg.meta_info and isinstance(msg.meta_info, dict):
            role = msg.meta_info.get("author_role", "").lower()
        # Identify user prompt with attachments.
        attachments = msg.meta_info.get("attachments") if msg.meta_info else None
        if role == "user" and attachments and isinstance(attachments, list) and len(attachments) > 0:
            transcript_msgs = []
            # Collect subsequent assistant (or tool) messages.
            j = i + 1
            while j < n:
                next_msg = messages[j]
                next_role = ""
                if next_msg.meta_info and isinstance(next_msg.meta_info, dict):
                    next_role = next_msg.meta_info.get("author_role", "").lower()
                if next_role in ("assistant", "tool"):
                    transcript_msgs.append(next_msg)
                    j += 1
                else:
                    break
            correlations.append((msg, transcript_msgs))
            i = j
        else:
            i += 1
    return correlations

def generate_html_for_conversation(conv, correlations, output_folder, timestamp_str):
    """
    Generate an HTML file for a single conversation.
    For each correlated block, display:
      - The user prompt (with its ID and HTML-escaped content)
      - The uploaded images (constructed from each attachment's id and name)
      - The assistant transcript messages (ID, HTML-escaped content, and YAML metadata)
    """
    conv_id_str = html.escape(str(conv.id))
    filename = f"conversation_{conv_id_str}_{timestamp_str}.html"
    output_path = os.path.join(output_folder, filename)

    html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Prompt & Transcript for Conversation {conv_id}</title>
  <style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .prompt-block {{ border: 1px solid #aaa; padding: 10px; margin-bottom: 20px; }}
    .transcript-block {{ border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; }}
    img {{ max-width: 100%; height: auto; display: block; margin: 5px 0; }}
    pre {{ background: #f8f8f8; padding: 10px; }}
    hr {{ border: 1px solid #ddd; margin: 20px 0; }}
  </style>
</head>
<body>
  <h1>Conversation ID: {conv_id}</h1>
""".format(conv_id=conv_id_str)
    if hasattr(conv, "title") and conv.title:
        html_content += "<h2>Title: {}</h2>\n".format(html.escape(conv.title))

    for prompt_msg, transcript_msgs in correlations:
        html_content += "<div class='prompt-block'>\n"
        html_content += f"<h3>User Prompt (Message ID: {html.escape(str(prompt_msg.id))})</h3>\n"
        html_content += f"<p><strong>Content:</strong> {html.escape(prompt_msg.content)}</p>\n"
        # Render each attachment as an image.
        attachments = prompt_msg.meta_info.get("attachments") if prompt_msg.meta_info else []
        for att in attachments:
            att_id = att.get("id")
            att_name = att.get("name")
            if att_id and att_name:
                # Construct the expected file path: "chat/file-<att_id>-<att_name>"
                file_path = os.path.join("chat", f"file-{att_id}-{att_name}")
                abs_path = os.path.abspath(file_path)
                file_url = "file://" + abs_path
                html_content += f"<img src='{file_url}' alt='Attachment {html.escape(att_id)}'>\n"
        html_content += "</div>\n"  # end prompt-block
        if transcript_msgs:
            html_content += "<div class='transcript-block'>\n"
            html_content += "<h3>Assistant Transcript(s):</h3>\n"
            for asm in transcript_msgs:
                html_content += f"<p><strong>Message ID:</strong> {html.escape(str(asm.id))}</p>\n"
                html_content += f"<p><strong>Content:</strong> {html.escape(asm.content)}</p>\n"
                meta = asm.meta_info if asm.meta_info else {}
                meta_yaml = yaml.dump(meta, default_flow_style=False, sort_keys=False)
                html_content += f"<pre>{html.escape(meta_yaml)}</pre>\n"
            html_content += "</div>\n"
        html_content += "<hr>\n"

    html_content += "</body>\n</html>\n"

    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"HTML file created for conversation {conv.id}: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Correlate user prompts with uploaded images and the subsequent assistant transcript responses."
    )
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of conversations to process (default: 10)")
    parser.add_argument("--conversation_id", type=str, default=None,
                        help="Optional specific conversation ID to process")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Folder to store the generated HTML files (default: 'output')")
    args = parser.parse_args()

    convs = get_conversations(args.limit, args.conversation_id)
    if not convs:
        print("No conversations found.")
        return

    # Create a subfolder for this run
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(args.output_folder, f"run_{timestamp_str}")
    os.makedirs(run_folder, exist_ok=True)

    for conv in convs:
        messages = get_messages_for_conversation(conv.id)
        correlations = correlate_prompt_and_transcript(messages)
        # Only include conversations that have at least one correlated block.
        if correlations:
            generate_html_for_conversation(conv, correlations, run_folder, timestamp_str)
        else:
            print(f"Conversation {conv.id} has no correlated prompt-transcript block.")

if __name__ == "__main__":
    main()
