"""
Utility functions for conversation operations.
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Union
from uuid import UUID

class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that can handle datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

def export_conversation_to_json(conversation, messages, output_path: str) -> None:
    """
    Export a conversation and its messages to a JSON file.
    
    Args:
        conversation: ConversationRead object
        messages: List of MessageRead objects
        output_path: Path to save the JSON file
    """
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Build the conversation dictionary
    conversation_dict = {
        "id": str(conversation.id),
        "title": conversation.title,
        "created_at": conversation.created_at,
        "meta_info": conversation.meta_info,
        "messages": [
            {
                "id": str(message.id),
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
                "meta_info": message.meta_info
            }
            for message in messages
        ]
    }
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(conversation_dict, f, cls=DateTimeEncoder, indent=2)