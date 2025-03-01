"""
Enhanced utilities for conversation parsing and timestamp handling.
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Set
from pathlib import Path

def extract_file_references(text: str) -> List[Dict[str, str]]:
    """
    Extract file references from message content.
    This will find both explicit references and implied ones.
    
    Returns:
        List of dicts with keys: 'file_id', 'file_name', 'reference_type'
    """
    references = []
    
    # Pattern for file-ID references (including ChatGPT style file-XXXX-filename)
    file_id_pattern = r'file-([a-zA-Z0-9]+)(?:-([^"\s]+))?'
    for match in re.finditer(file_id_pattern, text):
        file_id = match.group(1)
        file_name = match.group(2) if match.group(2) else None
        references.append({
            'file_id': file_id,
            'file_name': file_name,
            'reference_type': 'explicit'
        })
    
    # Pattern for PDF references
    pdf_pattern = r'(?:[\'"]\s*)?([a-zA-Z0-9_-]+\.pdf)(?:[\'"]\s*)?'
    for match in re.finditer(pdf_pattern, text):
        file_name = match.group(1)
        references.append({
            'file_id': None,
            'file_name': file_name,
            'reference_type': 'pdf_mention'
        })
    
    # General file references with extensions
    file_pattern = r'(?:[\'"]\s*)?([a-zA-Z0-9_-]+\.(docx?|xlsx?|pptx?|csv|txt|json|py|js|html?|css|md))(?:[\'"]\s*)?'
    for match in re.finditer(file_pattern, text):
        file_name = match.group(1)
        references.append({
            'file_id': None,
            'file_name': file_name,
            'reference_type': 'file_mention'
        })
    
    return references

def parse_message_timestamps(message: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract create_time and update_time from a message.
    
    Args:
        message: The message dictionary
        
    Returns:
        Tuple of (create_time, update_time) as floats or None
    """
    create_time = None
    update_time = None
    
    if 'create_time' in message and message['create_time'] is not None:
        try:
            create_time = float(message['create_time'])
        except (ValueError, TypeError):
            pass
    
    if 'update_time' in message and message['update_time'] is not None:
        try:
            update_time = float(message['update_time'])
        except (ValueError, TypeError):
            pass
            
    return create_time, update_time

def get_conversation_timestamps(conversation: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract create_time and update_time from a conversation.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Tuple of (create_time, update_time) as floats or None
    """
    create_time = None
    update_time = None
    
    if 'create_time' in conversation and conversation['create_time'] is not None:
        try:
            create_time = float(conversation['create_time'])
        except (ValueError, TypeError):
            pass
    
    if 'update_time' in conversation and conversation['update_time'] is not None:
        try:
            update_time = float(conversation['update_time'])
        except (ValueError, TypeError):
            pass
            
    return create_time, update_time

def get_conversation_message_timestamps(conversation: Dict[str, Any]) -> Tuple[List[float], List[float]]:
    """
    Extract all message timestamps from a conversation.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Tuple of (create_times, update_times) as lists of floats
    """
    create_times = []
    update_times = []
    
    mapping = conversation.get('mapping', {})
    
    for msg_id, msg_data in mapping.items():
        message = msg_data.get('message')
        if message:
            create_time, update_time = parse_message_timestamps(message)
            if create_time:
                create_times.append(create_time)
            if update_time:
                update_times.append(update_time)
    
    # Sort timestamps chronologically
    create_times.sort()
    update_times.sort()
    
    return create_times, update_times

def derive_conversation_timestamps(conversation: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """
    Get or derive the best timestamps for a conversation.
    
    Logic:
    1. Use explicit conversation timestamps if available
    2. If not, use the first and last message timestamps
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Tuple of (create_time, update_time) as floats or None
    """
    # Try to get explicit conversation timestamps
    conv_create_time, conv_update_time = get_conversation_timestamps(conversation)
    
    # Get all message timestamps
    msg_create_times, msg_update_times = get_conversation_message_timestamps(conversation)
    
    # Determine best create_time
    create_time = conv_create_time
    if create_time is None and msg_create_times:
        create_time = msg_create_times[0]  # First message timestamp
    
    # Determine best update_time
    update_time = conv_update_time
    if update_time is None:
        if msg_update_times:
            update_time = msg_update_times[-1]  # Last message update
        elif msg_create_times:
            update_time = msg_create_times[-1]  # Last message creation
    
    return create_time, update_time

def extract_media_from_conversation(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all media references from a conversation.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        List of media objects with metadata
    """
    media_references: List[Dict[str, Any]] = []
    seen_file_ids: Set[str] = set()
    
    mapping = conversation.get('mapping', {})
    
    for msg_id, msg_data in mapping.items():
        message = msg_data.get('message')
        if not message:
            continue
            
        # Get message metadata
        metadata = message.get('metadata', {})
        create_time, _ = parse_message_timestamps(message)
        
        # Extract from attachments in metadata
        if 'attachments' in metadata:
            for attachment in metadata['attachments']:
                file_id = attachment.get('id')
                file_name = attachment.get('name')
                
                if file_id and file_id not in seen_file_ids:
                    seen_file_ids.add(file_id)
                    
                    # Try to determine file path
                    file_path = None
                    if file_name:
                        # Check both variants of path construction
                        path1 = os.path.join("chat", f"file-{file_id}")
                        path2 = os.path.join("chat", f"file-{file_id}-{file_name}")
                        
                        if os.path.exists(path2):
                            file_path = path2
                        elif os.path.exists(path1):
                            file_path = path1
                    
                    # Determine media type
                    media_type = 'unknown'
                    if file_name:
                        _, ext = os.path.splitext(file_name)
                        ext = ext.lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']:
                            media_type = 'image'
                        elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
                            media_type = 'audio'
                        elif ext in ['.mp4', '.mov', '.avi', '.webm']:
                            media_type = 'video'
                        elif ext in ['.pdf']:
                            media_type = 'pdf'
                        else:
                            media_type = 'other'
                    
                    # Add to references
                    media_references.append({
                        'file_id': file_id,
                        'file_name': file_name,
                        'file_path': file_path,
                        'media_type': media_type,
                        'message_id': msg_id,
                        'create_time': create_time,
                        'source': 'attachment',
                        'exists': file_path is not None
                    })
        
        # Extract from message content
        content_parts = message.get('content', {}).get('parts', [])
        content_text = ""
        
        for part in content_parts:
            if isinstance(part, str):
                content_text += part
            elif isinstance(part, dict) and 'asset_pointer' in part:
                # Handle case where media is inline in the content
                asset_pointer = part.get('asset_pointer', '')
                if asset_pointer.startswith('file-service://file-'):
                    file_id = asset_pointer.replace('file-service://file-', '')
                    
                    if file_id and file_id not in seen_file_ids:
                        seen_file_ids.add(file_id)
                        
                        # Try to find the file
                        file_path = None
                        file_name = None
                        
                        # Check if the file exists
                        base_path = os.path.join("chat", f"file-{file_id}")
                        if os.path.exists(base_path):
                            file_path = base_path
                            # Try to determine the filename
                            parent_dir = os.path.dirname(base_path)
                            for filename in os.listdir(parent_dir):
                                if filename.startswith(f"file-{file_id}"):
                                    file_path = os.path.join(parent_dir, filename)
                                    file_name = filename.replace(f"file-{file_id}-", "")
                                    break
                        
                        # Determine media type based on part metadata
                        media_type = 'image'  # Default for inline content
                        
                        # Add to references
                        media_references.append({
                            'file_id': file_id,
                            'file_name': file_name,
                            'file_path': file_path,
                            'media_type': media_type,
                            'message_id': msg_id,
                            'create_time': create_time,
                            'source': 'inline',
                            'exists': file_path is not None
                        })
        
        # Extract file references from text content
        if content_text:
            references = extract_file_references(content_text)
            for ref in references:
                file_id = ref.get('file_id')
                file_name = ref.get('file_name')
                
                # Skip if already processed
                if file_id and file_id in seen_file_ids:
                    continue
                
                if file_id:
                    seen_file_ids.add(file_id)
                
                # For implicit references without file_id
                if not file_id and file_name:
                    # Check if we've already seen an equivalent file name
                    is_duplicate = False
                    for existing in media_references:
                        if existing.get('file_name') == file_name:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        continue
                
                # Try to determine file path for references with file_id
                file_path = None
                if file_id:
                    if file_name:
                        path = os.path.join("chat", f"file-{file_id}-{file_name}")
                        if os.path.exists(path):
                            file_path = path
                    else:
                        # Try just the ID pattern
                        path = os.path.join("chat", f"file-{file_id}")
                        if os.path.exists(path):
                            file_path = path
                
                # Determine media type
                media_type = 'unknown'
                if file_name:
                    _, ext = os.path.splitext(file_name)
                    ext = ext.lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif']:
                        media_type = 'image'
                    elif ext in ['.mp3', '.wav', '.ogg', '.flac']:
                        media_type = 'audio'
                    elif ext in ['.mp4', '.mov', '.avi', '.webm']:
                        media_type = 'video'
                    elif ext in ['.pdf']:
                        media_type = 'pdf'
                    else:
                        media_type = 'other'
                
                # Add to references
                media_references.append({
                    'file_id': file_id,
                    'file_name': file_name,
                    'file_path': file_path,
                    'media_type': media_type,
                    'message_id': msg_id,
                    'create_time': create_time,
                    'source': ref.get('reference_type', 'text_mention'),
                    'exists': file_path is not None
                })
    
    return media_references

def flatten_content(part: Any) -> str:
    """
    Flatten nested dict/list content into a single string.
    More sophisticated than the original to handle various content types.
    """
    if isinstance(part, str):
        return part
    elif isinstance(part, dict):
        # Skip media asset pointers
        if 'asset_pointer' in part:
            return ""
            
        # If "text" is present, prefer that
        if "text" in part:
            return flatten_content(part["text"])
            
        # For specific content types
        if "content_type" in part:
            if part["content_type"] == "image_asset_pointer":
                return "[Image]"  # Placeholder for images
            elif part["content_type"] == "file_asset_pointer":
                return f"[File: {part.get('file_name', 'Attachment')}]"
                
        return " ".join(flatten_content(v) for v in part.values())
    elif isinstance(part, list):
        return " ".join(flatten_content(item) for item in part)
    else:
        return str(part)

def parse_messages(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract messages from the ChatGPT-style 'mapping' structure.
    Enhanced version that maintains more metadata.
    """
    messages = []
    for node_id, node_data in mapping.items():
        message = node_data.get("message")
        if message:
            parts = message.get("content", {}).get("parts", [])
            content_parts = [flatten_content(p) for p in parts]
            flat_content = " ".join(content_parts).replace("\x00", "")
            
            # Get timestamp information
            create_time, update_time = parse_message_timestamps(message)
            
            # Extract all metadata
            metadata = message.get("metadata", {}).copy()
            
            # Add additional information from the message
            metadata.update({
                "author_role": message.get("author", {}).get("role", "unknown"),
                "status": message.get("status"),
                "end_turn": message.get("end_turn"),
                "weight": message.get("weight"),
                "recipient": message.get("recipient"),
                "channel": message.get("channel")
            })
            
            # Clean up None values
            metadata = {k: v for k, v in metadata.items() if v is not None}
            
            messages.append({
                "original_id": message.get("id"),
                "parent_id": node_data.get("parent"),
                "children": node_data.get("children", []),
                "author_role": message.get("author", {}).get("role", "unknown"),
                "content": flat_content,
                "create_time": create_time,
                "update_time": update_time,
                "raw_content": message.get("content"),
                "metadata": metadata
            })
    
    return messages