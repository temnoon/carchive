"""
ChatGPT Archive Adapter

This module provides adapters for importing data from ChatGPT conversation archives
into the carchive database.
"""
import json
import os
import uuid
import hashlib
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime

# SQLAlchemy models will be imported here
# from carchive.database.models import Conversation, Message, etc.

logger = logging.getLogger(__name__)

CHATGPT_PROVIDER_ID = "11111111-1111-1111-1111-111111111111"  # From our schema

class ChatGPTAdapter:
    """
    Adapter for processing ChatGPT conversation exports.
    Converts JSON data into database models and handles media files.
    """

    def __init__(self, 
                 conversation_file: str,
                 media_dir: str = None, 
                 target_media_dir: str = None):
        """
        Initialize the adapter.

        Args:
            conversation_file: Path to conversations.json
            media_dir: Directory containing media files
            target_media_dir: Directory to copy media files to
        """
        self.conversation_file = conversation_file
        self.media_dir = media_dir or os.path.dirname(conversation_file)
        self.target_media_dir = target_media_dir or os.path.join(os.path.dirname(self.media_dir), "media", "chatgpt")
        self.media_mapping = {}  # Maps original file IDs to new UUIDs
        
        # Ensure target directory exists
        os.makedirs(self.target_media_dir, exist_ok=True)

    def load_conversations(self) -> List[Dict]:
        """Load conversations from JSON file."""
        with open(self.conversation_file, 'r') as f:
            return json.load(f)

    def process_conversation(self, conv_data: Dict) -> Tuple[Dict, List[Dict], List[Dict], List[Dict]]:
        """
        Process a single conversation, returning structured data.
        
        Returns:
            Tuple of (conversation_data, messages_data, media_data, relations_data)
        """
        conv_id = str(uuid.uuid4())
        source_id = conv_data.get('conversation_id')
        
        logger.info(f"Processing conversation: {conv_data.get('title', 'Untitled')} ({source_id})")
        
        # Process timestamps correctly
        source_created_at = datetime.fromtimestamp(conv_data.get('create_time', 0))
        source_updated_at = datetime.fromtimestamp(conv_data.get('update_time', 0))
        
        # Create conversation record
        conversation = {
            'id': conv_id,
            'title': conv_data.get('title', 'Untitled Conversation'),
            'source_id': source_id,
            'provider_id': CHATGPT_PROVIDER_ID,
            'created_at': source_created_at,
            'updated_at': source_updated_at,
            'source_created_at': source_created_at,
            'source_updated_at': source_updated_at,
            'current_node_id': conv_data.get('current_node'),
            'is_archived': conv_data.get('is_archived', False),
            'is_starred': conv_data.get('is_starred', False),
            'model_info': json.dumps({
                'model_slug': conv_data.get('default_model_slug')
            }),
            'meta_info': json.dumps({k: v for k, v in conv_data.items() 
                                    if k not in ['mapping', 'title', 'conversation_id', 
                                                'create_time', 'update_time', 'current_node', 
                                                'is_archived', 'is_starred', 'default_model_slug']})
        }
        
        # Process messages and build message tree
        messages = []
        relations = []
        media_items = []
        
        mapping = conv_data.get('mapping', {})
        message_id_map = {}  # Maps original IDs to new UUIDs
        
        # First pass: create message records
        for msg_key, msg_data in mapping.items():
            if 'message' not in msg_data or msg_data['message'] is None:
                continue
                
            msg = msg_data['message']
            new_msg_id = str(uuid.uuid4())
            message_id_map[msg_key] = new_msg_id
            
            # Process message timestamps
            msg_created_at = datetime.fromtimestamp(msg.get('create_time', 0)) if msg.get('create_time') else source_created_at
            msg_updated_at = datetime.fromtimestamp(msg.get('update_time', 0)) if msg.get('update_time') else None
            
            # Extract content
            content_obj = msg.get('content', {})
            content_type = content_obj.get('content_type', 'text')
            content = ""
            
            if content_type == 'text':
                parts = content_obj.get('parts', [])
                content = "\n".join([str(part) for part in parts if part is not None])
            elif content_type == 'code':
                content = content_obj.get('text', "")
            elif content_type == 'multimodal_text':
                # Handle multimodal content specially
                parts = content_obj.get('parts', [])
                text_parts = []
                for idx, part in enumerate(parts):
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict):
                        if part.get('type') == 'image_url':
                            # Process image reference from image_url type
                            image_data = part.get('image_url', {})
                            media_result = self._process_media_reference(image_data, new_msg_id)
                            if media_result:
                                media_items.append(media_result)
                                text_parts.append(f"[Image: {media_result['media']['id']}]")
                        elif 'asset_pointer' in part:
                            # Process asset_pointer directly
                            asset_id = part.get('asset_pointer', '').split('://')[-1]
                            logger.info(f"Found asset pointer: {asset_id}")
                            # Create a placeholder for this asset
                            text_parts.append(f"[Asset: {asset_id}]")
                        elif part.get('content_type') == 'audio_asset_pointer' and 'asset_pointer' in part:
                            # Process audio asset
                            asset_id = part.get('asset_pointer', '').split('://')[-1]
                            logger.info(f"Found audio asset: {asset_id}")
                            text_parts.append(f"[Audio: {asset_id}]")
                        elif part.get('content_type') == 'audio_transcription':
                            # Add transcription text
                            transcription = part.get('text', '')
                            text_parts.append(f"Transcription: {transcription}")
                
                content = "\n".join(text_parts)
            
            # Extract role information
            author = msg.get('author', {})
            role = author.get('role', 'unknown')
            author_name = author.get('name')
            
            # Create message record
            message = {
                'id': new_msg_id,
                'conversation_id': conv_id,
                'source_id': msg.get('id'),
                'parent_id': None,  # Will be set in second pass
                'role': role,
                'author_name': author_name,
                'content': content,
                'content_type': content_type,
                'created_at': msg_created_at,
                'updated_at': msg_updated_at,
                'status': msg.get('status'),
                'end_turn': msg.get('end_turn', True),
                'weight': msg.get('weight', 1.0),
                'meta_info': json.dumps({k: v for k, v in msg.items()
                                        if k not in ['id', 'author', 'content', 'create_time', 
                                                   'update_time', 'status', 'end_turn', 'weight']})
            }
            
            messages.append(message)
            
            # Process attachments if present
            metadata = msg.get('metadata', {})
            attachments = metadata.get('attachments', [])
            if attachments:
                logger.info(f"Found {len(attachments)} attachments in message {msg.get('id')}")
                
            for idx, attachment in enumerate(attachments):
                media_item = self._process_attachment(attachment, new_msg_id, idx)
                if media_item:
                    media_items.append(media_item)
        
        # Second pass: establish parent-child relationships
        for msg_key, msg_data in mapping.items():
            if msg_key not in message_id_map:
                continue
                
            new_msg_id = message_id_map[msg_key]
            parent_key = msg_data.get('parent')
            
            if parent_key and parent_key in message_id_map:
                parent_id = message_id_map[parent_key]
                
                # Update message parent
                for msg in messages:
                    if msg['id'] == new_msg_id:
                        msg['parent_id'] = parent_id
                        break
                
                # Add relation
                relation = {
                    'id': str(uuid.uuid4()),
                    'parent_id': parent_id,
                    'child_id': new_msg_id,
                    'relationship_type': 'reply'
                }
                relations.append(relation)
        
        # Calculate first and last message times
        if messages:
            msg_times = [msg['created_at'] for msg in messages]
            first_msg_time = min(msg_times)
            last_msg_time = max(msg_times)
            
            conversation['first_message_time'] = first_msg_time
            conversation['last_message_time'] = last_msg_time
        
        return conversation, messages, media_items, relations

    def _process_attachment(self, attachment: Dict, message_id: str, position: int) -> Optional[Dict]:
        """
        Process a message attachment and return a media record.
        """
        attachment_id = attachment.get('id')
        if not attachment_id:
            return None
            
        # Determine original file path
        original_filename = attachment.get('name', '')
        file_path = None
        
        # ChatGPT archive files follow a pattern like "file-{ID}-{filename}"
        # where the ID isn't directly the attachment_id but contains it
        file_found = False
        for filename in os.listdir(self.media_dir):
            if filename.startswith("file-") and attachment_id in filename:
                file_path = os.path.join(self.media_dir, filename)
                file_found = True
                logger.info(f"Found media file for attachment {attachment_id}: {filename}")
                break
                
        # Try a more flexible matching approach if we didn't find an exact match
        if not file_found:
            for filename in os.listdir(self.media_dir):
                if filename.startswith("file-") and attachment_id[:8] in filename:
                    file_path = os.path.join(self.media_dir, filename)
                    file_found = True
                    logger.info(f"Found media file using partial ID for attachment {attachment_id}: {filename}")
                    break
        
        if not file_path:
            logger.warning(f"File not found for attachment {attachment_id}")
            return None
            
        # Create a UUID for the media item
        media_id = str(uuid.uuid4())
        
        # Calculate checksum
        checksum = self._calculate_file_checksum(file_path)
        
        # Determine mimetype from attachment or filename
        mime_type = attachment.get('mimeType', self._guess_mime_type(file_path))
        
        # Copy to target directory with UUID-based name
        ext = os.path.splitext(file_path)[1]
        new_filename = f"{media_id}{ext}"
        target_path = os.path.join(self.target_media_dir, new_filename)
        
        # Copy file if it doesn't exist yet
        if not os.path.exists(target_path):
            try:
                import shutil
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(file_path, target_path)
            except Exception as e:
                logger.error(f"Failed to copy file {file_path}: {e}")
                return None
        
        # Create media record
        media_item = {
            'id': media_id,
            'file_path': target_path,
            'original_file_name': original_filename,
            'original_file_id': attachment_id,
            'provider_id': CHATGPT_PROVIDER_ID,
            'mime_type': mime_type,
            'file_size': os.path.getsize(file_path),
            'checksum': checksum,
            'is_generated': False,
            'source_url': None,
            'meta_info': json.dumps(attachment)
        }
        
        # Create message_media relation
        message_media = {
            'id': str(uuid.uuid4()),
            'message_id': message_id,
            'media_id': media_id,
            'association_type': 'attachment',
            'position': position,
            'meta_info': json.dumps({})
        }
        
        # Store mapping for future reference
        self.media_mapping[attachment_id] = media_id
        
        return {
            'media': media_item,
            'message_media': message_media
        }

    def _process_media_reference(self, image_data: Dict, message_id: str) -> Optional[str]:
        """
        Process an inline image reference from multimodal content.
        Returns the media ID if successful.
        """
        # This handles URLs like "file-service://file-xxxx" or other references
        url = image_data.get('url', '')
        if not url.startswith('file-service://'):
            return None
            
        # Extract file ID from URL
        file_id = url.split('file-service://')[1]
        
        # Check if we've seen this file before
        if file_id in self.media_mapping:
            return self.media_mapping[file_id]
        
        # Look for the media file
        file_path = None
        file_found = False
        
        # Try to find the file in media_dir
        for filename in os.listdir(self.media_dir):
            if filename.startswith("file-") and file_id in filename:
                file_path = os.path.join(self.media_dir, filename)
                file_found = True
                logger.info(f"Found inline media file: {filename}")
                break
        
        # Try a more flexible matching approach
        if not file_found:
            for filename in os.listdir(self.media_dir):
                if filename.startswith("file-") and file_id[:8] in filename:
                    file_path = os.path.join(self.media_dir, filename)
                    file_found = True
                    logger.info(f"Found inline media file using partial ID: {filename}")
                    break
        
        if not file_path:
            logger.warning(f"File not found for inline media {file_id}")
            return None
        
        # Create a UUID for the media item
        media_id = str(uuid.uuid4())
        
        # Calculate checksum
        checksum = self._calculate_file_checksum(file_path)
        
        # Determine mimetype from filename
        mime_type = self._guess_mime_type(file_path)
        
        # Copy to target directory with UUID-based name
        ext = os.path.splitext(file_path)[1]
        new_filename = f"{media_id}{ext}"
        target_path = os.path.join(self.target_media_dir, new_filename)
        
        # Copy file if it doesn't exist yet
        if not os.path.exists(target_path):
            try:
                import shutil
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(file_path, target_path)
            except Exception as e:
                logger.error(f"Failed to copy file {file_path}: {e}")
                return None
        
        # Create media record
        media_item = {
            'id': media_id,
            'file_path': target_path,
            'original_file_name': os.path.basename(file_path),
            'original_file_id': file_id,
            'provider_id': CHATGPT_PROVIDER_ID,
            'mime_type': mime_type,
            'file_size': os.path.getsize(file_path),
            'checksum': checksum,
            'is_generated': False,
            'source_url': url,
            'meta_info': json.dumps(image_data)
        }
        
        # Create message_media relation
        message_media = {
            'id': str(uuid.uuid4()),
            'message_id': message_id,
            'media_id': media_id,
            'association_type': 'inline',
            'position': 0,
            'meta_info': json.dumps({})
        }
        
        # Store mapping for future reference
        self.media_mapping[file_id] = media_id
        
        return {
            'media': media_item,
            'message_media': message_media
        }

    def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum for a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _guess_mime_type(self, file_path: str) -> str:
        """Guess MIME type from file extension."""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
