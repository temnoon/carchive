"""
Claude conversations adapter for importing Anthropic Claude data into carchive.
"""

import json
import logging
import os
import re
import shutil
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import psycopg2

# Claude provider UUID - matches the one in the providers table
CLAUDE_PROVIDER_ID = "22222222-2222-2222-2222-222222222222"

logger = logging.getLogger(__name__)

class ClaudeAdapter:
    """Adapter for importing Claude conversations into the carchive database."""
    
    def __init__(self, 
                 conversations_file: str,
                 projects_file: Optional[str] = None,
                 users_file: Optional[str] = None,
                 media_dir: Optional[str] = None,
                 target_media_dir: Optional[str] = None):
        """
        Initialize the Claude adapter.
        
        Args:
            conversations_file: Path to the conversations.json file
            projects_file: Path to the projects.json file (optional)
            users_file: Path to the users.json file (optional)
            media_dir: Path to the directory containing media files
            target_media_dir: Path to the directory where media files should be copied
        """
        self.conversations_file = conversations_file
        self.projects_file = projects_file
        self.users_file = users_file
        self.media_dir = media_dir
        self.target_media_dir = target_media_dir
        
        # Load conversations data
        with open(self.conversations_file, 'r') as f:
            self.conversations_data = json.load(f)
            
        # Load projects data if available
        self.projects_data = None
        if self.projects_file and os.path.exists(self.projects_file):
            with open(self.projects_file, 'r') as f:
                self.projects_data = json.load(f)
                
        # Load users data if available
        self.users_data = None
        if self.users_file and os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users_data = json.load(f)
        
        # Map user IDs to names
        self.user_names = {}
        if self.users_data:
            for user in self.users_data:
                self.user_names[user['uuid']] = user['full_name']
                
        # Map project IDs to names
        self.project_names = {}
        if self.projects_data:
            for project in self.projects_data:
                self.project_names[project['uuid']] = project['name']
    
    def _parse_iso_timestamp(self, timestamp: str) -> float:
        """Convert ISO timestamp to Unix timestamp."""
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.timestamp()
    
    def _extract_conversation_metadata(self, conversation: Dict) -> Dict:
        """Extract metadata from a Claude conversation."""
        meta_info = {
            'source_conversation_id': conversation['uuid'],
            'is_anonymous': False,
            'create_time': self._parse_iso_timestamp(conversation['created_at']),
            'update_time': self._parse_iso_timestamp(conversation['updated_at']),
            'source_type': 'claude',
        }
        
        # Add account info if available
        if 'account' in conversation and 'uuid' in conversation['account']:
            meta_info['account_id'] = conversation['account']['uuid']
            if conversation['account']['uuid'] in self.user_names:
                meta_info['account_name'] = self.user_names[conversation['account']['uuid']]
        
        return meta_info
    
    def _extract_message_metadata(self, message: Dict) -> Dict:
        """Extract metadata from a Claude message."""
        meta_info = {
            'source_message_id': message['uuid'],
            'create_time': self._parse_iso_timestamp(message['created_at']),
            'update_time': self._parse_iso_timestamp(message['updated_at']),
            'sender': message['sender'],
        }
        
        # Add content metadata if available
        if 'content' in message and message['content']:
            meta_info['content_type'] = message['content'][0].get('type', 'text')
            
            # Add timestamps from content if available
            start_ts = message['content'][0].get('start_timestamp')
            stop_ts = message['content'][0].get('stop_timestamp')
            
            if start_ts:
                meta_info['content_start_time'] = self._parse_iso_timestamp(start_ts)
            if stop_ts:
                meta_info['content_stop_time'] = self._parse_iso_timestamp(stop_ts)
        
        return meta_info
    
    def _process_media_file(self, attachment: Dict, message_id: str) -> Optional[Tuple[Dict, str]]:
        """
        Process a media file attachment and copy to target directory if needed.
        Returns tuple of (media_data, file_path) if successful, None otherwise.
        """
        if not self.media_dir or not self.target_media_dir:
            return None
            
        # Claude attachments don't have standardized file paths in exports
        # We'd need to implement based on actual Claude attachment structure
        # This is a placeholder for future implementation
        return None
    
    def _process_conversation(self, conversation: Dict) -> Tuple[Dict, List[Dict], List[Dict], List[Dict]]:
        """
        Process a Claude conversation and its messages.
        Returns (conversation_data, messages_data, message_relations_data, media_data)
        """
        # Extract conversation metadata
        meta_info = self._extract_conversation_metadata(conversation)
        conversation_id = str(uuid.uuid4())
        
        # Create conversation record
        conversation_data = {
            'id': conversation_id,
            'title': conversation.get('name', 'Untitled Conversation'),
            'created_at': datetime.fromtimestamp(meta_info['create_time']),
            'updated_at': datetime.fromtimestamp(meta_info['update_time']),
            'provider_id': CLAUDE_PROVIDER_ID,
            'meta_info': json.dumps(meta_info)
        }
        
        # Process messages
        messages_data = []
        message_relations_data = []
        media_data = []
        
        # Track message IDs for parent-child relationships
        message_id_map = {}
        
        # Sort messages by timestamp to ensure correct ordering
        sorted_messages = sorted(
            conversation.get('chat_messages', []),
            key=lambda m: self._parse_iso_timestamp(m['created_at'])
        )
        
        prev_msg_id = None
        for i, message in enumerate(sorted_messages):
            msg_meta = self._extract_message_metadata(message)
            
            # Create new UUID for this message
            msg_id = str(uuid.uuid4())
            message_id_map[message['uuid']] = msg_id
            
            # Determine message role based on sender
            role = "user" if message['sender'] == "human" else "assistant"
            
            # Extract message content
            content = message['text']
            content_type = "text"  # Claude primarily uses text type
            
            # Create message record
            message_data = {
                'id': msg_id,
                'conversation_id': conversation_id,
                'source_id': message['uuid'],
                'parent_id': prev_msg_id,  # Link to previous message
                'role': role,
                'content': content,
                'content_type': content_type,
                'created_at': datetime.fromtimestamp(msg_meta['create_time']),
                'position': i,  # Position in conversation
                'meta_info': json.dumps(msg_meta)
            }
            messages_data.append(message_data)
            
            # Create message relation record if there's a parent
            if prev_msg_id:
                relation_data = {
                    'id': str(uuid.uuid4()),  # Add UUID primary key
                    'parent_id': prev_msg_id,
                    'child_id': msg_id,
                    'relationship_type': 'reply'  # Correct field name (not relation_type)
                    # Removed 'weight' field as it doesn't exist in schema
                }
                message_relations_data.append(relation_data)
            
            # Update prev_msg_id for next iteration
            prev_msg_id = msg_id
            
            # Process attachments if any
            for attachment in message.get('attachments', []):
                media_result = self._process_media_file(attachment, msg_id)
                if media_result:
                    media_info, file_path = media_result
                    media_data.append(media_info)
        
        return conversation_data, messages_data, message_relations_data, media_data
    
    def process_all(self):
        """Process all conversations and return data for database insertion."""
        all_conversations = []
        all_messages = []
        all_relations = []
        all_media = []
        
        for conversation in self.conversations_data:
            try:
                conv, msgs, relations, media = self._process_conversation(conversation)
                all_conversations.append(conv)
                all_messages.extend(msgs)
                all_relations.extend(relations)
                all_media.extend(media)
            except Exception as e:
                logger.error(f"Error processing conversation {conversation.get('uuid', 'unknown')}: {str(e)}")
        
        return all_conversations, all_messages, all_relations, all_media