# carchive2/ingestion/ingest.py

import json
import zipfile
import logging
import uuid
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union, Optional

from pydantic import BaseModel, ValidationError, Field
from sqlalchemy import cast
from sqlalchemy.dialects.postgresql import JSONB

from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, Media
from carchive.core.utils import contains_latex

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(name)s:%(message)s")

# --- Pydantic Schemas for Basic Validation ---

class ConversationEntry(BaseModel):
    id: Optional[str] = None
    conversation_id: Optional[str] = None
    title: Optional[str] = None
    messages: Optional[List[Any]] = None
    mapping: Optional[Dict[str, Any]] = None

    class Config:
        extra = 'allow'  # Allow extra fields not explicitly defined

class RawMessage(BaseModel):
    id: Optional[str] = None
    message_id: Optional[str] = None
    original_id: Optional[str] = None
    author_role: Optional[str] = "unknown"
    content: Optional[str] = ""
    create_time: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = 'allow'

# --- Existing Utility Functions ---

def flatten_content(part: Any) -> str:
    """
    Flatten nested dict/list content into a single string.
    """
    if isinstance(part, str):
        return part
    elif isinstance(part, dict):
        # If "text" is present, prefer that
        if "text" in part:
            return flatten_content(part["text"])
        return " ".join(flatten_content(v) for v in part.values())
    elif isinstance(part, list):
        return " ".join(flatten_content(item) for item in part)
    else:
        return str(part)

def parse_messages(mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract messages from the ChatGPT-style 'mapping' structure.
    """
    messages = []
    for node_id, node_data in mapping.items():
        message = node_data.get("message")
        if message:
            parts = message.get("content", {}).get("parts", [])
            content_parts = [flatten_content(p) for p in parts]
            flat_content = " ".join(content_parts).replace("\x00", "")
            messages.append({
                "original_id": message.get("id"),
                "parent_id": node_data.get("parent"),
                "author_role": message.get("author", {}).get("role", "unknown"),
                "content": flat_content,
                "create_time": message.get("create_time"),
                "metadata": message.get("metadata", {})
            })
    return messages

# --- Ingestion Functions ---

def ingest_file(file_path: Union[str, Path]):
    """
    Primary entry point for ingesting JSON or ZIP files.
    """
    file_path = Path(file_path)
    if file_path.suffix.lower() == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _process_data(data)
    elif file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path, "r") as z:
            for filename in z.namelist():
                if filename.endswith(".json"):
                    with z.open(filename) as f:
                        data = json.load(f)
                        _process_data(data)
    else:
        logger.error(f"Unsupported file format: {file_path.suffix}")

def _process_data(data: Union[Dict[str, Any], List[Any]]):
    """
    Internal method to process the loaded JSON data for conversations.
    """
    # Validate top-level structure using Pydantic (optional step)
    conversations = []
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict) and "conversations" in data:
        conversations = data["conversations"]
    else:
        logger.warning("Unrecognized top-level JSON structure; expecting a list or a dict with 'conversations'.")

    with get_session() as session:
        for convo_dict in conversations:
            try:
                conv_entry = ConversationEntry.parse_obj(convo_dict)
            except ValidationError as e:
                logger.error(f"Validation error for conversation: {e}")
                continue

            source_id = conv_entry.id or conv_entry.conversation_id
            if not source_id:
                logger.warning("Skipping conversation with no identifiable source ID.")
                continue

            existing_convo = session.query(Conversation).filter(
                cast(Conversation.meta_info, JSONB).contains({"source_conversation_id": source_id})
            ).first()
            if existing_convo:
                logger.info(f"Skipping conversation; already exists in DB for source_id={source_id}")
                continue

            new_convo_id = uuid.uuid4()
            conversation = Conversation(
                id=new_convo_id,
                title=conv_entry.title,
                meta_info={
                    "source_conversation_id": source_id,
                    **{k: v for k, v in conv_entry.dict(exclude={"id", "conversation_id", "title", "messages", "mapping"}).items() if v is not None}
                }
            )
            session.add(conversation)

            # Determine messages list
            messages_list = []
            if conv_entry.messages is not None and isinstance(conv_entry.messages, list):
                messages_list = conv_entry.messages
            elif conv_entry.mapping:
                messages_list = parse_messages(conv_entry.mapping)

            logger.debug(f"Found {len(messages_list)} messages for conversation source_id={source_id}")

            for msg_item in messages_list:
                try:
                    raw_msg = RawMessage.parse_obj(msg_item)
                except ValidationError as e:
                    logger.error(f"Validation error for message: {e}")
                    continue

                original_msg_id = raw_msg.id or raw_msg.message_id or raw_msg.original_id
                if not original_msg_id:
                    logger.warning("Skipping message with no identifiable source ID.")
                    continue

                existing_msg = session.query(Message).filter(
                    cast(Message.meta_info, JSONB).contains({"source_message_id": original_msg_id})
                ).first()
                if existing_msg:
                    logger.debug(f"Skipping message source_id={original_msg_id}; already in DB.")
                    continue

                new_msg_id = uuid.uuid4()
                msg_content = raw_msg.content or ""
                new_msg = Message(
                    id=new_msg_id,
                    conversation_id=new_convo_id,
                    content=msg_content,
                    meta_info={
                        "source_message_id": original_msg_id,
                        "author_role": raw_msg.author_role,
                        "contains_latex": contains_latex(msg_content),
                        **raw_msg.metadata
                    }
                )

                if raw_msg.create_time:
                    try:
                        ts = float(raw_msg.create_time)
                        new_msg.created_at = datetime.fromtimestamp(ts)
                    except ValueError:
                        pass

                session.add(new_msg)

                # Handle attachments if they exist
                if raw_msg.metadata and 'attachments' in raw_msg.metadata:
                    for attachment in raw_msg.metadata['attachments']:
                        att_id = attachment.get("id")
                        att_name = attachment.get("name")
                        
                        if att_id and att_name:
                            # Construct the relative file path
                            file_path = os.path.join("chat", f"file-{att_id}-{att_name}")
                            
                            # Check if the file exists
                            if os.path.exists(file_path):
                                # Determine media type from extension
                                _, ext = os.path.splitext(att_name)
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
                                
                                # Check if media already exists
                                existing_media = session.query(Media).filter(
                                    Media.original_file_id == att_id
                                ).first()
                                
                                if not existing_media:
                                    media_id = uuid.uuid4()
                                    media = Media(
                                        id=media_id,
                                        message_id=new_msg.id,
                                        file_path=file_path,
                                        media_type=media_type,
                                        created_at=datetime.utcnow(),
                                        original_file_id=att_id,
                                        file_name=f"file-{att_id}-{att_name}",
                                        is_generated=False
                                    )
                                    session.add(media)
                                    logger.info(f"Added media attachment {att_id} for message {new_msg.id}")
                                else:
                                    # Update the existing media entry
                                    existing_media.message_id = new_msg.id
                                    logger.info(f"Linked existing media {att_id} to message {new_msg.id}")
                        else:
                            logger.warning(f"Incomplete attachment info in message metadata: {attachment}")

                word_count = len(msg_content.split())
                logger.info(f"Added new message source_id={original_msg_id} with {word_count} words.")

            try:
                session.commit()
                logger.debug("Committed conversation/messages successfully.")
            except Exception as e:
                session.rollback()
                logger.error(f"Error committing data for source_conversation_id={source_id}: {e}")
