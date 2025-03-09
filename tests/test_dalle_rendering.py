#!/usr/bin/env python3
"""
Test script to verify DALL-E image rendering in a conversation.

This script:
1. Finds messages with [Asset: file-XXX] references in a conversation
2. Renders them to HTML
3. Checks if the images are properly included in the output

Usage:
    python tests/test_dalle_rendering.py [conversation_id]
"""
import sys
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy import or_

from carchive.database.session import get_session
from carchive.database.models import Message, Media, MessageMedia, Conversation
from carchive.rendering.markdown_renderer import MarkdownRenderer
from carchive.rendering.html_renderer import HTMLRenderer


def find_asset_references(session, limit=5):
    """Find messages with [Asset: file-XXX] references."""
    messages = session.query(Message).filter(
        Message.content.like('%[Asset: file-%')
    ).limit(limit).all()
    
    return messages


def render_message_html(message):
    """Render a message's content to HTML."""
    md_renderer = MarkdownRenderer()
    content_markdown = md_renderer.render(message.content, message_id=message.id)
    
    # Use the HTML renderer to properly render images
    html_renderer = HTMLRenderer()
    content_html = html_renderer.render_text(content_markdown)
    
    # Simple HTML wrapper
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>DALL-E Rendering Test</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .message {{ padding: 10px; margin-bottom: 20px; border: 1px solid #ddd; }}
        .message-content {{ margin-top: 10px; }}
        img {{ max-width: 100%; }}
    </style>
</head>
<body>
    <h1>DALL-E Rendering Test</h1>
    <div class="message">
        <h2>Message ID: {message.id}</h2>
        <p>Role: {message.role}</p>
        <div class="message-content">
            {content_html}
        </div>
    </div>
</body>
</html>
    """
    return html


def extract_asset_ids(content):
    """Extract asset IDs from a message content."""
    pattern = r'\[Asset: (file-[a-zA-Z0-9]+)\]'
    return re.findall(pattern, content)


def check_media_for_id(session, file_id):
    """Check if a file ID has a corresponding media record."""
    bare_id = file_id.replace('file-', '')
    
    # Try exact match
    media = session.query(Media).filter_by(original_file_id=file_id).first()
    if media:
        return f"Found exact match: {media.id}, path: {media.file_path}"
    
    # Try bare ID
    media = session.query(Media).filter_by(original_file_id=bare_id).first()
    if media:
        return f"Found match with bare ID: {media.id}, path: {media.file_path}"
    
    # Try partial match
    media = session.query(Media).filter(
        Media.original_file_id.like(f"%{bare_id}%")
    ).first()
    if media:
        return f"Found partial match: {media.id}, path: {media.file_path}"
    
    return "No match found"


def save_test_html(message, html):
    """Save test HTML to a file."""
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    file_path = output_dir / f"dalle_test_message_{message.id}.html"
    with open(file_path, "w") as f:
        f.write(html)
    
    return file_path


def main():
    """Main function."""
    # Get conversation ID from args or use all conversations
    conversation_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    with get_session() as session:
        # Find messages with asset references
        if conversation_id:
            messages = session.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.content.like('%[Asset: file-%')
            ).limit(5).all()
            
            if not messages:
                print(f"No messages with asset references found in conversation {conversation_id}")
                return
        else:
            messages = find_asset_references(session)
            
            if not messages:
                print("No messages with asset references found")
                return
        
        print(f"Found {len(messages)} messages with asset references")
        
        # Process each message
        for message in messages:
            print(f"\nProcessing message {message.id}")
            print(f"Role: {message.role}")
            print(f"Content preview: {message.content[:100]}...")
            
            # Extract asset IDs
            asset_ids = extract_asset_ids(message.content)
            print(f"Found {len(asset_ids)} asset references: {', '.join(asset_ids)}")
            
            # Check media for each asset ID
            for asset_id in asset_ids:
                result = check_media_for_id(session, asset_id)
                print(f"- {asset_id}: {result}")
            
            # Render HTML
            html = render_message_html(message)
            
            # Save to file
            file_path = save_test_html(message, html)
            print(f"Test HTML saved to {file_path}")


if __name__ == "__main__":
    main()