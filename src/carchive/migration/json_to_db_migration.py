"""
Migration script to rebuild the database directly from conversations.json.

This script:
1. Reads from the original conversations.json file
2. Queries the existing database to get UUIDs for conversations and messages
3. Rebuilds the conversations and messages tables with correct timestamp handling
4. Preserves relationships with media, embeddings, etc.

Usage:
    python -m carchive.migration.json_to_db_migration --json-path path/to/conversations.json [--dry-run]
"""

import argparse
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from carchive.database.session import get_session
from carchive.database.models import (
    Conversation, Message, Media, MessageMedia, Embedding, Chunk, 
    Collection, CollectionItem, AgentOutput
)
from carchive.conversation_utils import (
    derive_conversation_timestamps,
    extract_media_from_conversation,
    parse_messages
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Migration mappings
convo_id_mapping = {}  # Maps source_conversation_id to database UUID
message_id_mapping = {}  # Maps source_message_id to database UUID
processed_conversations = set()  # Tracks processed conversations to avoid duplicates

def load_conversations_json(json_path: str) -> List[Dict[str, Any]]:
    """Load conversations from the original JSON file."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "conversations" in data:
            return data["conversations"]
        else:
            logger.error("Unrecognized JSON structure. Expected a list or dict with 'conversations' key.")
            return []
    except Exception as e:
        logger.error(f"Error loading conversations JSON: {e}")
        return []

def get_existing_mappings(session: Session) -> Tuple[Dict[str, uuid.UUID], Dict[str, uuid.UUID]]:
    """
    Query the database to get existing UUIDs for conversations and messages.
    
    Returns:
        Tuple of (conversation_mapping, message_mapping)
        Where each mapping is from source_*_id to database UUID
    """
    # Get conversation mappings
    conversation_mapping = {}
    query = select(Conversation.id, Conversation.meta_info)
    for convo_id, meta_info in session.execute(query):
        if meta_info and "source_conversation_id" in meta_info:
            source_id = meta_info["source_conversation_id"]
            conversation_mapping[source_id] = convo_id
    
    # Get message mappings
    message_mapping = {}
    query = select(Message.id, Message.meta_info)
    for msg_id, meta_info in session.execute(query):
        if meta_info and "source_message_id" in meta_info:
            source_id = meta_info["source_message_id"]
            message_mapping[source_id] = msg_id
    
    logger.info(f"Found {len(conversation_mapping)} existing conversations and {len(message_mapping)} existing messages in database")
    return conversation_mapping, message_mapping

def process_conversation(
    session: Session,
    convo_dict: Dict[str, Any],
    convo_mapping: Dict[str, uuid.UUID],
    msg_mapping: Dict[str, uuid.UUID],
    dry_run: bool = False
) -> Optional[uuid.UUID]:
    """
    Process a single conversation: either update existing or create new with correct timestamps.
    
    Args:
        session: Database session
        convo_dict: Conversation dictionary from JSON
        convo_mapping: Mapping of source_conversation_id to database UUID
        msg_mapping: Mapping of source_message_id to database UUID
        dry_run: If True, don't make changes to database
        
    Returns:
        UUID of the conversation in the database, or None if processing failed
    """
    # Get key identifiers
    source_id = convo_dict.get('id') or convo_dict.get('conversation_id')
    if not source_id:
        logger.warning("Skipping conversation with no identifiable source ID")
        return None
    
    # Skip if already processed in this run
    if source_id in processed_conversations:
        logger.debug(f"Skipping already processed conversation {source_id}")
        return None
    
    processed_conversations.add(source_id)
    
    # Get timestamps
    create_time, update_time = derive_conversation_timestamps(convo_dict)
    
    # Extract messages
    mapping = convo_dict.get('mapping', {})
    if not mapping:
        logger.warning(f"Skipping conversation {source_id} with no message mapping")
        return None
    
    messages_list = parse_messages(mapping)
    if not messages_list:
        logger.warning(f"Skipping conversation {source_id} with no valid messages")
        return None
    
    # Check if conversation exists in database
    db_convo_id = convo_mapping.get(source_id)
    
    # Prepare conversation metadata
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
    
    # Set up conversation created_at
    created_at = datetime.now()
    if create_time is not None:
        created_at = datetime.fromtimestamp(create_time)
    
    if dry_run:
        logger.info(f"DRY RUN: Would {'update' if db_convo_id else 'create'} conversation {source_id}")
        # Use existing ID or generate a new one for dry run
        return db_convo_id or uuid.uuid4()
    
    # Create or update conversation
    if db_convo_id:
        # Update existing conversation
        convo = session.get(Conversation, db_convo_id)
        if convo:
            convo.title = convo_dict.get('title')
            convo.meta_info = meta_info
            convo.created_at = created_at
            logger.info(f"Updated conversation {source_id} (DB ID: {db_convo_id})")
        else:
            logger.warning(f"Conversation {source_id} has mapping but not found in DB")
            return None
    else:
        # Create new conversation with new UUID
        db_convo_id = uuid.uuid4()
        convo = Conversation(
            id=db_convo_id,
            title=convo_dict.get('title'),
            meta_info=meta_info,
            created_at=created_at
        )
        session.add(convo)
        convo_mapping[source_id] = db_convo_id
        logger.info(f"Created new conversation {source_id} (DB ID: {db_convo_id})")
    
    # Process messages
    for msg_item in messages_list:
        original_msg_id = msg_item.get('original_id')
        if not original_msg_id:
            logger.warning("Skipping message with no identifiable source ID")
            continue
        
        # Check if message exists
        db_msg_id = msg_mapping.get(original_msg_id)
        
        # Prepare message metadata
        msg_meta_info = {
            "source_message_id": original_msg_id,
            "author_role": msg_item.get('author_role', 'unknown'),
            "parent_id": msg_item.get('parent_id'),
            "children": msg_item.get('children', []),
            **msg_item.get('metadata', {})
        }
        
        # Set created_at time if available
        msg_create_time = msg_item.get('create_time')
        msg_created_at = datetime.now()
        if msg_create_time is not None:
            msg_created_at = datetime.fromtimestamp(msg_create_time)
        
        if db_msg_id:
            # Update existing message
            msg = session.get(Message, db_msg_id)
            if msg:
                msg.content = msg_item.get('content', '')
                msg.meta_info = msg_meta_info
                msg.created_at = msg_created_at
                logger.debug(f"Updated message {original_msg_id} (DB ID: {db_msg_id})")
            else:
                logger.warning(f"Message {original_msg_id} has mapping but not found in DB")
        else:
            # Create new message
            db_msg_id = uuid.uuid4()
            msg = Message(
                id=db_msg_id,
                conversation_id=db_convo_id,
                content=msg_item.get('content', ''),
                meta_info=msg_meta_info,
                created_at=msg_created_at
            )
            session.add(msg)
            msg_mapping[original_msg_id] = db_msg_id
            logger.debug(f"Created new message {original_msg_id} (DB ID: {db_msg_id})")
    
    return db_convo_id

def update_relations(session: Session, dry_run: bool = False):
    """
    Update relationships for media, embeddings, etc. that were linked to old 
    conversations or messages.
    
    This is necessary only if we've created new UUIDs for conversations/messages.
    """
    if dry_run:
        logger.info("DRY RUN: Would update relationships")
        return
    
    # Update media_message relationships
    for source_msg_id, db_msg_id in message_id_mapping.items():
        # This will only update records that have message_ids we've changed
        stmt = (
            select(MessageMedia)
            .join(Message, MessageMedia.message_id == Message.id)
            .filter(Message.meta_info["source_message_id"].as_string() == source_msg_id)
        )
        
        for media_msg in session.execute(stmt).scalars().all():
            media_msg.message_id = db_msg_id
    
    # Update chunks
    for source_msg_id, db_msg_id in message_id_mapping.items():
        stmt = (
            select(Chunk)
            .join(Message, Chunk.message_id == Message.id)
            .filter(Message.meta_info["source_message_id"].as_string() == source_msg_id)
        )
        
        for chunk in session.execute(stmt).scalars().all():
            chunk.message_id = db_msg_id
    
    # Update embeddings
    for source_msg_id, db_msg_id in message_id_mapping.items():
        stmt = (
            select(Embedding)
            .filter(Embedding.parent_message_id.isnot(None))
            .join(Message, Embedding.parent_message_id == Message.id)
            .filter(Message.meta_info["source_message_id"].as_string() == source_msg_id)
        )
        
        for embedding in session.execute(stmt).scalars().all():
            embedding.parent_message_id = db_msg_id
    
    # Update collection items
    for source_convo_id, db_convo_id in convo_id_mapping.items():
        stmt = (
            select(CollectionItem)
            .join(Conversation, CollectionItem.conversation_id == Conversation.id)
            .filter(Conversation.meta_info["source_conversation_id"].as_string() == source_convo_id)
        )
        
        for item in session.execute(stmt).scalars().all():
            item.conversation_id = db_convo_id

def migrate_json_to_db(json_path: str, dry_run: bool = False, skip_relations: bool = False):
    """
    Main migration function.
    
    Args:
        json_path: Path to conversations.json file
        dry_run: If True, don't make changes to database
        skip_relations: If True, skip updating relationships (useful for permission issues)
    """
    # Load conversations from JSON
    conversations = load_conversations_json(json_path)
    if not conversations:
        logger.error("No conversations found in JSON or error loading file")
        return False
    
    logger.info(f"Loaded {len(conversations)} conversations from JSON")
    
    # Start migration
    with get_session() as session:
        try:
            # Get existing mappings
            convo_mapping, msg_mapping = get_existing_mappings(session)
            global convo_id_mapping, message_id_mapping
            convo_id_mapping = convo_mapping.copy()
            message_id_mapping = msg_mapping.copy()
            
            # Process each conversation
            num_processed = 0
            for i, convo_dict in enumerate(conversations):
                if (i+1) % 100 == 0:
                    logger.info(f"Processing conversation {i+1}/{len(conversations)}...")
                
                process_conversation(
                    session, convo_dict, convo_id_mapping, message_id_mapping, dry_run
                )
                
                # Commit every 100 conversations to avoid large transactions
                if (i+1) % 100 == 0 and not dry_run:
                    session.commit()
                    logger.info(f"Committed batch {i+1}/{len(conversations)}")
                
                num_processed += 1
            
            # Update relationships if not skipped
            if not skip_relations:
                try:
                    logger.info("Updating relationships between messages, media, and other entities...")
                    update_relations(session, dry_run)
                    logger.info("Relationships updated successfully")
                except Exception as e:
                    logger.error(f"Error updating relationships: {e}")
                    logger.warning("Continuing without updating relationships. Some references may be inconsistent.")
                    # We don't fail the migration because of relationship updates
                    if not dry_run:
                        session.commit()
            else:
                logger.info("Skipping relationship updates as requested")
            
            # Final commit
            if not dry_run:
                session.commit()
                logger.info(f"Migration complete. Processed {num_processed} conversations.")
            else:
                logger.info(f"DRY RUN complete. Would have processed {num_processed} conversations.")
            
            return True
        
        except Exception as e:
            if not dry_run:
                session.rollback()
            logger.error(f"Error during migration: {e}", exc_info=True)
            return False

def main():
    parser = argparse.ArgumentParser(description="Migrate conversations from JSON to database with correct timestamps")
    parser.add_argument("--json-path", required=True, help="Path to conversations.json file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    args = parser.parse_args()
    
    # Verify file exists
    json_path = Path(args.json_path)
    if not json_path.exists():
        logger.error(f"File {json_path} does not exist")
        return 1
    
    logger.info(f"Starting migration from {json_path} (dry_run: {args.dry_run})")
    success = migrate_json_to_db(str(json_path), args.dry_run)
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())