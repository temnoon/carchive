"""Direct archive export file accessor component.

This module provides functionality to access and verify contents of chat archive
export files (ZIP) without fully extracting them.
"""

import os
import json
import zipfile
from typing import Optional, List, Dict, Any, Tuple, Iterator
from pathlib import Path
from datetime import datetime


class ArchiveAccessor:
    """Class for directly accessing and exploring chat archive exports."""

    def __init__(self, archive_path: str):
        """Initialize with path to archive ZIP file.
        
        Args:
            archive_path: Path to the archive zip file
        
        Raises:
            FileNotFoundError: If the archive file doesn't exist
            zipfile.BadZipFile: If the file is not a valid ZIP file
        """
        self.archive_path = archive_path
        
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Archive file '{archive_path}' not found")
        
        # Validate it's a zip file
        try:
            with zipfile.ZipFile(archive_path, 'r'):
                pass
        except zipfile.BadZipFile:
            raise zipfile.BadZipFile(f"'{archive_path}' is not a valid ZIP file")
    
    def get_conversations_file_path(self) -> Optional[str]:
        """Find the conversations.json file path within the archive.
        
        Returns:
            Path to conversations.json within the archive or None if not found
        """
        with zipfile.ZipFile(self.archive_path, 'r') as zipf:
            for file in zipf.namelist():
                if file.endswith('conversations.json'):
                    return file
        return None
    
    def get_conversations(self) -> List[Dict[str, Any]]:
        """Load all conversations from the archive.
        
        Returns:
            List of conversation dictionaries
            
        Raises:
            ValueError: If conversations.json is not found
        """
        conv_file = self.get_conversations_file_path()
        if not conv_file:
            raise ValueError("No conversations.json found in archive")
        
        with zipfile.ZipFile(self.archive_path, 'r') as zipf:
            with zipf.open(conv_file) as f:
                return json.load(f)
    
    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific conversation by ID.
        
        Args:
            conversation_id: The ID of the conversation to find
            
        Returns:
            Conversation dict if found, None otherwise
        """
        conversations = self.get_conversations()
        for conv in conversations:
            if conv.get('conversation_id') == conversation_id:
                return conv
        return None
    
    def get_conversation_summary(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of conversation metadata.
        
        Args:
            conversation: Conversation dictionary
            
        Returns:
            Dictionary containing key metadata
        """
        return {
            'id': conversation.get('conversation_id', 'Unknown'),
            'title': conversation.get('title', 'Untitled'),
            'create_time': conversation.get('create_time'),
            'update_time': conversation.get('update_time'),
            'model': conversation.get('default_model_slug', 'Unknown model'),
            'message_count': len(conversation.get('mapping', {}))
        }
    
    def get_messages(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all messages from a conversation in order.
        
        Args:
            conversation: Conversation dictionary
            
        Returns:
            List of message dictionaries with parent-child relationships preserved
        """
        messages = []
        mapping = conversation.get('mapping', {})
        
        # Find root messages (no parent)
        root_messages = []
        for msg_id, msg_data in mapping.items():
            if not msg_data.get('parent'):
                root_messages.append(msg_id)
        
        # Process each message tree
        for root_id in root_messages:
            self._extract_message_tree(mapping, root_id, 0, messages)
        
        return messages
    
    def _extract_message_tree(self, mapping: Dict[str, Any], msg_id: str, 
                             depth: int, messages: List[Dict[str, Any]]) -> None:
        """Recursively extract message tree with proper depth indication.
        
        Args:
            mapping: Message mapping dictionary
            msg_id: Current message ID
            depth: Current depth in the tree
            messages: List to append messages to
        """
        # Handle missing message ID
        if not msg_id or msg_id not in mapping:
            return
            
        msg_data = mapping.get(msg_id, {})
        message = msg_data.get('message', {})
        
        # Add depth information
        msg_with_depth = {
            'id': msg_id,
            'depth': depth,
            'data': message,
            'parent': msg_data.get('parent'),
            'children': msg_data.get('children', [])
        }
        
        messages.append(msg_with_depth)
        
        # Recursively process children (with safety check)
        children = msg_data.get('children', [])
        if children and isinstance(children, list):
            for child_id in children:
                if child_id and isinstance(child_id, str):
                    self._extract_message_tree(mapping, child_id, depth + 1, messages)

    def get_media_references(self, conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find all media references in a conversation.
        
        Args:
            conversation: Conversation dictionary
            
        Returns:
            List of media reference dictionaries
        """
        media_refs = []
        mapping = conversation.get('mapping', {})
        
        for msg_id, msg_data in mapping.items():
            try:
                message = msg_data.get('message', {})
                if not message:
                    continue
                    
                metadata = message.get('metadata', {})
                # Safety check for None metadata
                if not metadata:
                    continue
                    
                attachments = metadata.get('attachments', [])
                # Safety check for None or non-list attachments
                if not attachments or not isinstance(attachments, list):
                    continue
                
                for attachment in attachments:
                    if not attachment:
                        continue
                        
                    media_refs.append({
                        'id': attachment.get('id', 'unknown'),
                        'name': attachment.get('name', 'unnamed'),
                        'mime_type': attachment.get('mimeType', 'unknown'),
                        'message_id': msg_id
                    })
            except Exception:
                # Skip problematic messages
                continue
        
        return media_refs
    
    def get_media_files(self) -> List[str]:
        """Get a list of all media files in the archive.
        
        Returns:
            List of media file paths within the archive
        """
        with zipfile.ZipFile(self.archive_path, 'r') as zipf:
            files = zipf.namelist()
            
            # Filter for likely media files
            return [f for f in files if f.startswith('dalle-generations/') or 
                                      f.startswith('files/') or 
                                      f.endswith('.png') or 
                                      f.endswith('.jpg') or 
                                      f.endswith('.jpeg') or 
                                      f.endswith('.webp') or
                                      f.endswith('.pdf')]
                                      
    def get_media_mapping(self) -> List[Dict[str, Any]]:
        """Get a comprehensive mapping of all media files with their associations.
        
        Returns:
            List of dictionaries with media file information including:
            - path: Path in archive
            - filename: Original filename
            - file_id: File ID if extractable from path
            - references: List of message references including conversation_id, message_id, etc.
        """
        # First get all conversations to search for references
        try:
            conversations = self.get_conversations()
        except Exception:
            conversations = []
            
        # First build message relationships (parent/child) for quick lookup
        # This helps us find the assistant message that contains a tool message
        message_parents = {}
        assistant_children = {}  # Assistant message ID -> List of tool message IDs
        
        for conv in conversations:
            conv_id = conv.get('conversation_id', 'unknown')
            mapping = conv.get('mapping', {})
            
            # Build parent-child relationships
            for msg_id, msg_data in mapping.items():
                parent_id = msg_data.get('parent')
                if parent_id:
                    message_parents[msg_id] = parent_id
                    
                    # Track assistant -> tool relationships specifically
                    parent_data = mapping.get(parent_id, {})
                    parent_message = parent_data.get('message')
                    parent_message = parent_message if parent_message is not None else {}
                    parent_role = parent_message.get('author', {}).get('role', '')
                    
                    current_message = msg_data.get('message')
                    current_message = current_message if current_message is not None else {}
                    current_role = current_message.get('author', {}).get('role', '')
                    
                    if parent_role == 'assistant' and current_role == 'tool':
                        assistant_children.setdefault(parent_id, []).append(msg_id)
            
        # Build lookup of file_id -> [reference info]
        file_id_map = {}
        
        for conv in conversations:
            conv_id = conv.get('conversation_id', 'unknown')
            mapping = conv.get('mapping', {})
            
            for msg_id, msg_data in mapping.items():
                try:
                    message = msg_data.get('message', {})
                    if not message:
                        continue
                        
                    role = message.get('author', {}).get('role', '')
                    
                    # For relationship tracking
                    parent_id = msg_data.get('parent')
                    parent_role = None
                    assistant_parent_id = None
                    
                    # Find parent message role
                    if parent_id and parent_id in mapping:
                        parent_data = mapping.get(parent_id, {})
                        parent_message = parent_data.get('message')
                        parent_message = parent_message if parent_message is not None else {}
                        parent_role = parent_message.get('author', {}).get('role', '')
                    
                    # For tool messages, find the assistant parent (for DALL-E images)
                    if role == 'tool':
                        current_id = msg_id
                        # Go up the parent chain until we find an assistant message
                        while current_id in message_parents:
                            parent_id = message_parents[current_id]
                            parent_data = mapping.get(parent_id, {})
                            parent_message = parent_data.get('message')
                            parent_message = parent_message if parent_message is not None else {}
                            parent_role = parent_message.get('author', {}).get('role', '')
                            
                            if parent_role == 'assistant':
                                assistant_parent_id = parent_id
                                break
                            
                            current_id = parent_id
                    
                    # Check for attachments in message metadata
                    metadata = message.get('metadata')
                    metadata = metadata if metadata is not None else {}
                    attachments = metadata.get('attachments')
                    attachments = attachments if attachments is not None else []
                    
                    for attachment in attachments:
                        if attachment and 'id' in attachment:
                            file_id = attachment.get('id')
                            if file_id:
                                # Store conversation and message context
                                file_id_map.setdefault(file_id, []).append({
                                    'conversation_id': conv_id,
                                    'message_id': msg_id,
                                    'file_name': attachment.get('name', ''),
                                    'mime_type': attachment.get('mimeType', ''),
                                    'role': role,
                                    'parent_id': parent_id,
                                    'parent_role': parent_role,
                                    'assistant_parent_id': assistant_parent_id
                                })
                    
                    # Also check for image_asset_pointer in content
                    content = message.get('content')
                    content = content if content is not None else {}
                    if content and isinstance(content, dict):
                        content_type = content.get('content_type')
                        if content_type == 'multimodal_text' and 'parts' in content:
                            for part in content.get('parts', []):
                                if isinstance(part, dict) and 'asset_pointer' in part:
                                    # Extract file ID from asset_pointer
                                    asset_pointer = part.get('asset_pointer', '')
                                    if 'file-service://' in asset_pointer:
                                        file_id = asset_pointer.replace('file-service://', '')
                                        file_id_map.setdefault(file_id, []).append({
                                            'conversation_id': conv_id,
                                            'message_id': msg_id,
                                            'file_name': 'embedded_image',
                                            'mime_type': 'image/unknown',
                                            'role': role,
                                            'parent_id': parent_id,
                                            'parent_role': parent_role,
                                            'assistant_parent_id': assistant_parent_id
                                        })
                                        
                except Exception as e:
                    # Skip problematic messages
                    continue
        
        # Now get all media files and match them
        result = []
        media_files = self.get_media_files()
        
        for file_path in media_files:
            entry = {
                'path': file_path,
                'filename': file_path.split('/')[-1],
                'file_id': None,
                'references': []
            }
            
            # Try to extract file ID from path if available (with safety checks)
            filename = entry.get('filename', '')
            if filename and isinstance(filename, str) and filename.startswith('file-'):
                # The file ID is the "file-XXXXX" prefix before any original filename
                # Pattern is generally: file-[alphanumeric string]-[original filename]
                # Extract just the file ID portion (file-XXXXX)
                try:
                    import re
                    match = re.match(r'(file-[a-zA-Z0-9]+)', filename)
                    if match:
                        entry['file_id'] = match.group(1)
                except Exception:
                    # If regex fails, skip extraction
                    pass
            
            # Look for all file IDs that might be in this path (with comprehensive safety checks)
            for file_id, references in file_id_map.items():
                try:
                    # Skip invalid file IDs
                    if not file_id or not isinstance(file_id, str):
                        continue
                        
                    # For media files, we need exact file ID matching
                    # The file ID should be at the beginning of the filename (after directory name)
                    if not file_path or not isinstance(file_path, str):
                        continue
                        
                    file_parts = file_path.split('/')
                    if not file_parts:
                        continue
                        
                    file_basename = file_parts[-1]
                    if file_basename.startswith(file_id):
                        # Make sure references is a list
                        if references and isinstance(references, list):
                            # Create a safe copy of references
                            safe_refs = []
                            for ref in references:
                                if ref and isinstance(ref, dict):
                                    safe_refs.append(ref)
                            
                            if 'references' not in entry:
                                entry['references'] = []
                            entry['references'].extend(safe_refs)
                            
                            if not entry.get('file_id'):
                                entry['file_id'] = file_id
                except Exception:
                    # Skip any problematic entries
                    continue
            
            result.append(entry)
            
        return result
    
    def find_media_file_by_id(self, file_id: str) -> Optional[str]:
        """Find a media file by its ID.
        
        Args:
            file_id: ID of the media file to find
            
        Returns:
            Path to the media file within the archive, or None if not found
        """
        media_files = self.get_media_files()
        for file in media_files:
            if file_id in file:
                return file
        return None
    
    def extract_media_file(self, file_path: str, target_dir: str) -> str:
        """Extract a specific media file to the target directory.
        
        Args:
            file_path: Path to the file within the archive
            target_dir: Directory to extract to
            
        Returns:
            Path to the extracted file
            
        Raises:
            KeyError: If the file doesn't exist in the archive
        """
        with zipfile.ZipFile(self.archive_path, 'r') as zipf:
            zipf.extract(file_path, target_dir)
            return os.path.join(target_dir, file_path)
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get overall statistics about the archive.
        
        Returns:
            Dictionary with archive statistics
        """
        try:
            conversations = self.get_conversations()
            media_files = self.get_media_files()
            
            # Count messages
            total_messages = 0
            for conv in conversations:
                total_messages += len(conv.get('mapping', {}))
            
            return {
                'conversations': len(conversations),
                'messages': total_messages,
                'media_files': len(media_files),
                'archive_size': os.path.getsize(self.archive_path)
            }
        except Exception as e:
            return {'error': str(e)}

    def iterate_all_messages(self) -> Iterator[Tuple[str, Dict]]:
        """Iterate through all messages in all conversations.
        
        Yields:
            Tuples of (conversation_id, message_dict)
        """
        conversations = self.get_conversations()
        
        for conv in conversations:
            conv_id = conv.get('conversation_id', 'unknown')
            mapping = conv.get('mapping', {})
            
            for msg_id, msg_data in mapping.items():
                yield (conv_id, msg_data.get('message', {}))
    
    def search_messages(self, query: str) -> List[Tuple[str, Dict]]:
        """Search for messages containing the query string.
        
        Args:
            query: String to search for
            
        Returns:
            List of tuples with (conversation_id, message_dict)
        """
        results = []
        query = query.lower()
        
        for conv_id, message in self.iterate_all_messages():
            content = message.get('content', {})
            parts = content.get('parts', [])
            
            # Check all parts for the query
            for part in parts:
                if isinstance(part, str) and query in part.lower():
                    results.append((conv_id, message))
                    break
        
        return results