"""
Enhanced conversation service with improved timestamp handling and media reference extraction.
"""

import json
import zipfile
import logging
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union, Optional, Set, Tuple

from sqlalchemy import cast, func, desc
from sqlalchemy.dialects.postgresql import JSONB

from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, Media, MessageMedia
from carchive.conversation_utils import (
    derive_conversation_timestamps,
    extract_media_from_conversation,
    parse_messages
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

class ConversationService:
    """Service for managing conversations and related objects."""
    
    @staticmethod
    def ingest_file(file_path: Union[str, Path], 
                    skip_existing: bool = True,
                    extract_media: bool = True,
                    verbose: bool = False) -> Tuple[int, int]:
        """
        Ingest conversations from a JSON or ZIP file.
        
        Args:
            file_path: Path to the JSON or ZIP file
            skip_existing: Whether to skip conversations that already exist in the database
            extract_media: Whether to extract and create references to media files
            verbose: Whether to output verbose logging
        
        Returns:
            Tuple of (conversations_ingested, messages_ingested)
        """
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
            
        file_path = Path(file_path)
        
        conversations_ingested = 0
        messages_ingested = 0
        
        if file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ingested_convos, ingested_msgs = ConversationService._process_data(
                data, skip_existing, extract_media
            )
            conversations_ingested += ingested_convos
            messages_ingested += ingested_msgs
            
        elif file_path.suffix.lower() == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                for filename in z.namelist():
                    if filename.endswith(".json"):
                        with z.open(filename) as f:
                            data = json.load(f)
                            ingested_convos, ingested_msgs = ConversationService._process_data(
                                data, skip_existing, extract_media
                            )
                            conversations_ingested += ingested_convos
                            messages_ingested += ingested_msgs
        else:
            logger.error(f"Unsupported file format: {file_path.suffix}")
        
        return conversations_ingested, messages_ingested
    
    @staticmethod
    def _process_data(data: Union[Dict[str, Any], List[Any]], 
                      skip_existing: bool = True,
                      extract_media: bool = True) -> Tuple[int, int]:
        """
        Process the loaded JSON data for conversations.
        
        Args:
            data: The loaded JSON data
            skip_existing: Whether to skip conversations that already exist in the database
            extract_media: Whether to extract and create references to media files
            
        Returns:
            Tuple of (conversations_ingested, messages_ingested)
        """
        conversations_ingested = 0
        messages_ingested = 0
        
        # Determine conversations list structure
        conversations = []
        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict) and "conversations" in data:
            conversations = data["conversations"]
        else:
            logger.warning("Unrecognized top-level JSON structure; expecting a list or a dict with 'conversations'.")
        
        logger.info(f"Found {len(conversations)} conversations to process")
        
        with get_session() as session:
            for i, convo_dict in enumerate(conversations):
                # Progress reporting
                if (i+1) % 100 == 0:
                    logger.info(f"Processing conversation {i+1}/{len(conversations)}...")
                
                # Get key identifiers
                source_id = convo_dict.get('id') or convo_dict.get('conversation_id')
                if not source_id:
                    logger.warning("Skipping conversation with no identifiable source ID.")
                    continue
                
                # Check for existing conversation
                if skip_existing:
                    existing_convo = session.query(Conversation).filter(
                        cast(Conversation.meta_info, JSONB).contains({"source_conversation_id": source_id})
                    ).first()
                    if existing_convo:
                        logger.debug(f"Skipping conversation; already exists in DB for source_id={source_id}")
                        continue
                
                # Generate timestamps
                create_time, update_time = derive_conversation_timestamps(convo_dict)
                
                # Extract messages
                mapping = convo_dict.get('mapping', {})
                if not mapping:
                    logger.warning(f"Skipping conversation {source_id} with no message mapping.")
                    continue
                
                messages_list = parse_messages(mapping)
                if not messages_list:
                    logger.warning(f"Skipping conversation {source_id} with no valid messages.")
                    continue
                
                logger.debug(f"Found {len(messages_list)} messages for conversation {source_id}")
                
                # Extract all media references if requested
                media_references = []
                if extract_media:
                    media_references = extract_media_from_conversation(convo_dict)
                    logger.debug(f"Found {len(media_references)} media references for conversation {source_id}")
                
                # Create conversation record
                new_convo_id = uuid.uuid4()
                meta_info = {
                    "source_conversation_id": source_id,
                    **{k: v for k, v in convo_dict.items() 
                       if k not in ["id", "conversation_id", "title", "messages", "mapping", "create_time", "update_time"]}
                }
                
                # Add timestamp info to meta_info
                if create_time is not None:
                    meta_info["create_time"] = create_time
                if update_time is not None:
                    meta_info["update_time"] = update_time
                
                conversation = Conversation(
                    id=new_convo_id,
                    title=convo_dict.get('title'),
                    meta_info=meta_info
                )
                
                # Set created_at explicitly if create_time is available
                if create_time is not None:
                    conversation.created_at = datetime.fromtimestamp(create_time)
                
                session.add(conversation)
                conversations_ingested += 1
                
                # Create message records
                for msg_item in messages_list:
                    original_msg_id = msg_item.get('original_id')
                    if not original_msg_id:
                        logger.warning("Skipping message with no identifiable source ID.")
                        continue
                    
                    new_msg_id = uuid.uuid4()
                    msg_content = msg_item.get('content', '')
                    
                    # Prepare message metadata
                    msg_meta_info = {
                        "source_message_id": original_msg_id,
                        "author_role": msg_item.get('author_role', 'unknown'),
                        "parent_id": msg_item.get('parent_id'),
                        "children": msg_item.get('children', []),
                        **msg_item.get('metadata', {})
                    }
                    
                    new_msg = Message(
                        id=new_msg_id,
                        conversation_id=new_convo_id,
                        content=msg_content,
                        meta_info=msg_meta_info
                    )
                    
                    # Set created_at time if available
                    msg_create_time = msg_item.get('create_time')
                    if msg_create_time is not None:
                        new_msg.created_at = datetime.fromtimestamp(msg_create_time)
                    
                    session.add(new_msg)
                    messages_ingested += 1
                    
                    # Find media associated with this message
                    if extract_media:
                        for media_ref in media_references:
                            if media_ref.get('message_id') == original_msg_id:
                                file_id = media_ref.get('file_id')
                                file_name = media_ref.get('file_name')
                                file_path = media_ref.get('file_path')
                                media_type = media_ref.get('media_type', 'unknown')
                                source = media_ref.get('source', 'unknown')
                                
                                # Check if the media already exists by original_file_id
                                existing_media = None
                                if file_id:
                                    existing_media = session.query(Media).filter(
                                        Media.original_file_id == file_id
                                    ).first()
                                
                                if not existing_media:
                                    # Create new media record
                                    media_id = uuid.uuid4()
                                    media = Media(
                                        id=media_id,
                                        file_path=file_path or "",
                                        media_type=media_type,
                                        original_file_id=file_id,
                                        file_name=file_name,
                                        is_generated=False
                                    )
                                    
                                    # Set creation time if available
                                    media_create_time = media_ref.get('create_time')
                                    if media_create_time is not None:
                                        media.created_at = datetime.fromtimestamp(media_create_time)
                                    
                                    session.add(media)
                                    
                                    # Create message-media association
                                    assoc = MessageMedia(
                                        id=uuid.uuid4(),
                                        message_id=new_msg_id,
                                        media_id=media_id,
                                        association_type=source
                                    )
                                    session.add(assoc)
                                    logger.debug(f"Added media {file_id or file_name} for message {original_msg_id}")
                                else:
                                    # Create association to existing media
                                    assoc = MessageMedia(
                                        id=uuid.uuid4(),
                                        message_id=new_msg_id,
                                        media_id=existing_media.id,
                                        association_type=source
                                    )
                                    session.add(assoc)
                                    logger.debug(f"Linked existing media {file_id or file_name} to message {original_msg_id}")
                
                # Commit after each conversation to avoid large transactions
                try:
                    session.commit()
                    logger.debug(f"Committed conversation {source_id} with {len(messages_list)} messages")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Error committing data for source_conversation_id={source_id}: {e}")
        
        return conversations_ingested, messages_ingested
    
    @staticmethod
    def extract_media_references_only(file_path: Union[str, Path], output_path: Union[str, Path] = None):
        """
        Extract only media references from conversations JSON without ingesting into the database.
        Useful for analysis or planning migration.
        
        Args:
            file_path: Path to the JSON or ZIP file
            output_path: Optional path to save extracted references as JSON
            
        Returns:
            List of media references
        """
        file_path = Path(file_path)
        all_references = []
        
        if file_path.suffix.lower() == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                conversations = []
                if isinstance(data, list):
                    conversations = data
                elif isinstance(data, dict) and "conversations" in data:
                    conversations = data["conversations"]
                
                for i, convo_dict in enumerate(conversations):
                    # Progress reporting
                    if (i+1) % 100 == 0:
                        logger.info(f"Processing conversation {i+1}/{len(conversations)}...")
                        
                    source_id = convo_dict.get('id') or convo_dict.get('conversation_id')
                    if not source_id:
                        continue
                    
                    media_refs = extract_media_from_conversation(convo_dict)
                    if media_refs:
                        # Add conversation context to each reference
                        for ref in media_refs:
                            ref['conversation_id'] = source_id
                        
                        all_references.extend(media_refs)
        
        # Save to output file if requested
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(all_references, f, indent=2)
            logger.info(f"Saved {len(all_references)} media references to {output_path}")
        
        return all_references