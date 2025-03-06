"""
Migration Service for carchive

Provides functionality to migrate data from various sources into the carchive database.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from tqdm import tqdm
import psycopg2
import psycopg2.extras

from .chatgpt_adapter import ChatGPTAdapter
from .claude_adapter import ClaudeAdapter, CLAUDE_PROVIDER_ID

logger = logging.getLogger(__name__)

class MigrationService:
    """
    Service to migrate data from various sources into the carchive database.
    """

    def __init__(self, db_connection_string: str):
        """
        Initialize the migration service.
        
        Args:
            db_connection_string: PostgreSQL connection string
        """
        self.db_connection_string = db_connection_string
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection."""
        self.conn = psycopg2.connect(self.db_connection_string)
        self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        logger.info("Connected to database")

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")

    def migrate_chatgpt_archive(self, archive_path: str, media_dir: str = None, 
                              target_media_dir: str = None, dalle_dir: str = None) -> Dict[str, int]:
        """
        Migrate a ChatGPT archive to the carchive database.
        
        Args:
            archive_path: Path to conversations.json
            media_dir: Directory containing media files
            target_media_dir: Directory to copy media files to
            dalle_dir: Directory containing DALL-E generated images
            
        Returns:
            Statistics dict with counts of imported items
        """
        adapter = ChatGPTAdapter(
            conversation_file=archive_path,
            media_dir=media_dir,
            target_media_dir=target_media_dir,
            dalle_dir=dalle_dir
        )
        
        # Load conversations
        logger.info(f"Loading conversations from {archive_path}")
        conversations = adapter.load_conversations()
        logger.info(f"Found {len(conversations)} conversations")
        
        # Connect to database
        self.connect()
        
        total_messages = 0
        total_media = 0
        total_relations = 0
        
        try:
            # Register ChatGPT provider
            self.cursor.execute("SELECT id FROM providers WHERE id = %s", ("11111111-1111-1111-1111-111111111111",))
            if not self.cursor.fetchone():
                logger.info("Registering ChatGPT provider")
                self.cursor.execute(
                    "INSERT INTO providers (id, name, description) VALUES (%s, %s, %s)",
                    ("11111111-1111-1111-1111-111111111111", "chatgpt", "ChatGPT exports from OpenAI")
                )
                self.conn.commit()
            
            # Process each conversation
            for conv_data in tqdm(conversations, desc="Migrating conversations"):
                try:
                    # Process conversation data
                    conversation, messages, media_items, relations = adapter.process_conversation(conv_data)
                    
                    # Insert conversation
                    self._insert_conversation(conversation)
                    
                    # Insert messages
                    for message in messages:
                        self._insert_message(message)
                    
                    # Insert message relations
                    for relation in relations:
                        self._insert_message_relation(relation)
                    
                    # Insert media
                    for media_item in media_items:
                        self._insert_media(media_item['media'])
                        self._insert_message_media(media_item['message_media'])
                    
                    # Update totals
                    total_messages += len(messages)
                    total_media += len(media_items)
                    total_relations += len(relations)
                    
                    # Commit transaction
                    self.conn.commit()
                    
                except Exception as e:
                    # Roll back on error
                    self.conn.rollback()
                    logger.error(f"Error processing conversation {conv_data.get('conversation_id')}: {e}")
            
            logger.info("Migration completed successfully")
            
            # Return statistics
            return {
                "conversations": len(conversations),
                "messages": total_messages,
                "relations": total_relations,
                "media": total_media
            }
            
        except Exception as e:
            # Roll back on error
            self.conn.rollback()
            logger.error(f"Error during migration: {e}")
            raise
            
        finally:
            # Close database connection
            self.close()
    
    def migrate_claude_archive(self, 
                             conversations_file: str, 
                             projects_file: Optional[str] = None,
                             users_file: Optional[str] = None,
                             media_dir: Optional[str] = None, 
                             target_media_dir: Optional[str] = None) -> Dict[str, int]:
        """
        Migrate a Claude archive to the carchive database.
        
        Args:
            conversations_file: Path to conversations.json
            projects_file: Path to projects.json (optional)
            users_file: Path to users.json (optional)
            media_dir: Directory containing media files
            target_media_dir: Directory to copy media files to
            
        Returns:
            Statistics dict with counts of imported items
        """
        # Initialize adapter
        adapter = ClaudeAdapter(
            conversations_file=conversations_file,
            projects_file=projects_file,
            users_file=users_file,
            media_dir=media_dir,
            target_media_dir=target_media_dir
        )
        
        # Process all data
        logger.info(f"Loading conversations from {conversations_file}")
        conversations, messages, relations, media = adapter.process_all()
        
        logger.info(f"Found {len(conversations)} conversations")
        logger.info(f"Found {len(messages)} messages")
        logger.info(f"Found {len(relations)} message relations")
        logger.info(f"Found {len(media)} media files")
        
        # Connect to database
        self.connect()
        
        try:
            # Register Claude provider
            self.cursor.execute("SELECT id FROM providers WHERE id = %s", (CLAUDE_PROVIDER_ID,))
            if not self.cursor.fetchone():
                logger.info("Registering Claude provider")
                self.cursor.execute(
                    "INSERT INTO providers (id, name, description) VALUES (%s, %s, %s)",
                    (CLAUDE_PROVIDER_ID, "claude", "Claude exports from Anthropic")
                )
                self.conn.commit()
            
            # Group data by conversation to handle transactions per conversation
            conv_messages = {}
            conv_relations = {}
            conv_media = {}
            
            # Organize messages by conversation_id
            for msg in messages:
                conv_id = msg['conversation_id']
                if conv_id not in conv_messages:
                    conv_messages[conv_id] = []
                conv_messages[conv_id].append(msg)
            
            # Organize message relations by associated conversation
            # This requires some inference since relations don't directly store conversation_id
            for rel in relations:
                # Find the message and get its conversation_id
                # We'll use child_id to find the conversation_id
                child_id = rel['child_id']
                conv_id = None
                for msg in messages:
                    if msg['id'] == child_id:
                        conv_id = msg['conversation_id']
                        break
                
                if conv_id:
                    if conv_id not in conv_relations:
                        conv_relations[conv_id] = []
                    conv_relations[conv_id].append(rel)
            
            # Insert conversations one at a time, with all their related data
            logger.info(f"Inserting {len(conversations)} conversations")
            for conv_data in tqdm(conversations, desc="Migrating conversations"):
                try:
                    # Start a new transaction for this conversation
                    conv_id = conv_data['id']
                    
                    # Insert conversation
                    self._insert_conversation(conv_data)
                    
                    # Insert this conversation's messages
                    for msg_data in conv_messages.get(conv_id, []):
                        self._insert_message(msg_data)
                    
                    # Insert this conversation's message relations
                    for rel_data in conv_relations.get(conv_id, []):
                        self._insert_message_relation(rel_data)
                    
                    # Insert this conversation's media (if implemented)
                    # (current implementation doesn't have media)
                    
                    # Commit this conversation's transaction
                    self.conn.commit()
                    
                except Exception as e:
                    # Roll back on error
                    self.conn.rollback()
                    logger.error(f"Error processing conversation {conv_data.get('id')}: {e}")
            
            # Insert any remaining media files (if any)
            if media:
                logger.info(f"Inserting {len(media)} media files")
                try:
                    for media_data in tqdm(media, desc="Migrating media"):
                        # Insert media
                        self._insert_media(media_data)
                    # Commit media changes
                    self.conn.commit()
                except Exception as e:
                    self.conn.rollback()
                    logger.error(f"Error inserting media: {str(e)}")
            
            # Return statistics
            return {
                "conversations": len(conversations),
                "messages": len(messages),
                "relations": len(relations),
                "media": len(media)
            }
            
        except Exception as e:
            # Roll back on error
            self.conn.rollback()
            logger.error(f"Error during migration: {e}")
            raise
            
        finally:
            # Close database connection
            self.close()
    
    def _insert_conversation(self, conversation: Dict):
        """Insert conversation into the database."""
        columns = ', '.join(conversation.keys())
        placeholders = ', '.join(['%s'] * len(conversation))
        query = f"INSERT INTO conversations ({columns}) VALUES ({placeholders})"
        self.cursor.execute(query, list(conversation.values()))
    
    def _insert_message(self, message: Dict):
        """Insert message into the database."""
        columns = ', '.join(message.keys())
        placeholders = ', '.join(['%s'] * len(message))
        query = f"INSERT INTO messages ({columns}) VALUES ({placeholders})"
        self.cursor.execute(query, list(message.values()))
    
    def _insert_message_relation(self, relation: Dict):
        """Insert message relation into the database."""
        columns = ', '.join(relation.keys())
        placeholders = ', '.join(['%s'] * len(relation))
        query = f"INSERT INTO message_relations ({columns}) VALUES ({placeholders})"
        self.cursor.execute(query, list(relation.values()))
    
    def _insert_media(self, media: Dict):
        """Insert media into the database."""
        columns = ', '.join(media.keys())
        placeholders = ', '.join(['%s'] * len(media))
        query = f"INSERT INTO media ({columns}) VALUES ({placeholders})"
        self.cursor.execute(query, list(media.values()))
    
    def _insert_message_media(self, message_media: Dict):
        """Insert message_media relation into the database."""
        columns = ', '.join(message_media.keys())
        placeholders = ', '.join(['%s'] * len(message_media))
        query = f"INSERT INTO message_media ({columns}) VALUES ({placeholders})"
        self.cursor.execute(query, list(message_media.values()))
