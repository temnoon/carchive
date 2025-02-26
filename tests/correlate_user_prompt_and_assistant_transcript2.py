#!/usr/bin/env python3
"""
Correlate User Prompts with Uploaded Images to Subsequent Assistant Transcript Responses

For each conversation (optionally filtered by --conversation_id and limited by --limit),
this script:
  1. Retrieves the conversation's messages (sorted by created_at).
  2. Identifies user prompt messages (where meta_info indicates author_role=="user")
     that include an attachments list (i.e. uploaded images).
  3. For each such user prompt, collects the subsequent assistant (or tool) messages
     as the transcript block.
  4. Only conversations with at least one correlated block (i.e. a user prompt with attachments
     and at least one subsequent assistant message) are output.
  5. Generates one HTML file per conversation in a timestamp-named subfolder under the given output folder.
     Each HTML file displays:
       - The conversation ID (and title, if available)
       - For each correlated block: the user prompt (ID and content, HTML-escaped) with its attachments
         rendered as images (using constructed file paths), and the subsequent assistant transcript messages.
  6. At the end, a summary is printed showing how many HTML files were generated.

Usage:
  python tests/correlate_user_prompt_and_assistant_transcript.py --limit 10 --output_folder "output"
  (Optionally add --conversation_id <conv_id> to process a specific conversation.)
"""

import os
import argparse
import html
import yaml  # Requires PyYAML (pip install PyYAML)
from datetime import datetime

from carchive.database.session import get_session
from carchive.database.models import Conversation, Message

def get_conversations(limit, conv_id=None):
    """Retrieve conversations ordered by created_at descending."""
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

def get_message_role(msg):
    """Return the lower-case role from the message's meta_info (if available)."""
    if msg.meta_info and isinstance(msg.meta_info, dict):
        return msg.meta_info.get("author_role", "").lower()
    return ""

def correlate_prompt_and_transcript(messages):
    """
    Given a list of messages (sorted by created_at) for one conversation,
    identify a user prompt that includes uploaded images (detected via a non-empty "attachments"
    list in meta_info) and then collect subsequent assistant (or tool) messages as the transcript block.

    Returns a list of tuples: (user_message, [assistant_message, ...]).
    """
    correlations = []
    n = len(messages)
    i = 0
    while i < n:
        msg = messages[i]
        role = get_message_role(msg)
        attachments = msg.meta_info.get("attachments") if msg.meta_info else None
        if role == "user" and attachments and isinstance(attachments, list) and len(attachments) > 0:
            transcript_msgs = []
            j = i + 1
            while j < n:
                next_msg = messages[j]
                next_role = get_message_role(next_msg)
                if next_role in ("assistant", "tool"):
                    transcript_msgs.append(next_msg)
                    j += 1
                else:
                    break
            # Only add correlation if there's at least one assistant response
            if transcript_msgs:
                correlations.append((msg, transcript_msgs))
            i = j
        else:
            i += 1
    return correlations

def generate_html_for_conversation(conv, correlations, output_folder, timestamp_str):
    """
    Generate an HTML file for a single conversation that shows:
      - The conversation ID (and title, if available)
      - For each correlated block, the user prompt (with HTML-escaped content) and its attachments rendered as images,
        and the subsequent assistant transcript messages (with HTML-escaped content and YAML-formatted metadata).
    """
    conv_id_str = html.escape(str(conv.id))
    filename = f"conversation_{conv_id_str}_{timestamp_str}.html"
    output_path = os.path.join(output_folder, filename)

    # Double curly braces in style block for literal braces.
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

    for user_msg, transcript_msgs in correlations:
        html_content += "<div class='prompt-block'>\n"
        html_content += f"<h3>User Prompt (Message ID: {html.escape(str(user_msg.id))})</h3>\n"
        html_content += f"<p><strong>Content:</strong> {html.escape(user_msg.content)}</p>\n"
        # Render attachments as images.
        attachments = user_msg.meta_info.get("attachments") if user_msg.meta_info else []
        if attachments:
            for att in attachments:
                att_id = att.get("id")
                att_name = att.get("name")
                if att_id and att_name:
                    # Construct the file path: assume "chat/file-<att_id>-<att_name>"
                    file_path = os.path.join("chat", f"{att_id}-{att_name}")
                    abs_path = os.path.abspath(file_path)
                    file_url = "file://" + abs_path
                    html_content += f"<img src='{file_url}' alt='Attachment {html.escape(att_id)}'>\n"
        else:
            html_content += "<p><em>No attachments found.</em></p>\n"
        html_content += "</div>\n"  # end prompt block

        if transcript_msgs:
            html_content += "<div class='transcript-block'>\n"
            html_content += "<h3>Assistant Transcript(s):</h3>\n"
            for asm in transcript_msgs:
                html_content += f"<p><strong>Message ID:</strong> {html.escape(str(asm.id))}</p>\n"
                html_content += f"<p><strong>Content:</strong> {html.escape(asm.content)}</p>\n"
                meta_yaml = yaml.dump(asm.meta_info, default_flow_style=False, sort_keys=False) if asm.meta_info else "None"
                html_content += f"<pre>{html.escape(meta_yaml)}</pre>\n"
            html_content += "</div>\n"
        html_content += "<hr>\n"

    html_content += "</body>\n</html>\n"

    with open(output_path, "w") as f:
        f.write(html_content)
    print(f"HTML file created for conversation {conv.id}: {output_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Correlate user prompts (with uploaded images) and subsequent assistant transcripts, and generate one HTML file per conversation."
    )
    parser.add_argument("--limit", type=int, default=10,
                        help="Number of conversations to process (default: 10)")
    parser.add_argument("--conversation_id", type=str, default=None,
                        help="Optional: process only a specific conversation ID")
    parser.add_argument("--output_folder", type=str, default="output",
                        help="Folder to store the output HTML files (default: 'output')")
    args = parser.parse_args()

    convs = get_conversations(args.limit, args.conversation_id)
    if not convs:
        print("No conversations found.")
        return

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_folder = os.path.join(args.output_folder, f"run_{run_timestamp}")
    os.makedirs(run_folder, exist_ok=True)

    file_count = 0
    for conv in convs:
        messages = get_messages_for_conversation(conv.id)
        correlations = correlate_prompt_and_transcript(messages)
        # Only include conversation if there is at least one correlated prompt-transcript block.
        if correlations:
            generate_html_for_conversation(conv, correlations, run_folder, run_timestamp)
            file_count += 1

    print(f"Summary: Generated {file_count} HTML file(s) with user-uploaded images and subsequent assistant messages.")

if __name__ == "__main__":
    main()
