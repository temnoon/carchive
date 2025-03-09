"""Unit tests for the ArchiveAccessor component."""

import os
import unittest
import tempfile
import zipfile
import json
from pathlib import Path

from carchive.archive import ArchiveAccessor

class TestArchiveAccessor(unittest.TestCase):
    """Test cases for the ArchiveAccessor component."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary ZIP file for testing
        self.temp_dir = tempfile.mkdtemp()
        self.zip_path = os.path.join(self.temp_dir, "test_archive.zip")
        
        # Create a mock conversations.json file
        conversations_data = [
            {
                "conversation_id": "test-conv-1",
                "title": "Test Conversation 1",
                "create_time": 1709740800,  # March 2024
                "update_time": 1709827200,
                "mapping": {
                    "msg-1": {
                        "id": "msg-1",
                        "parent": None,
                        "children": ["msg-2"],
                        "message": {
                            "id": "msg-1",
                            "author": {"role": "user"},
                            "content": {
                                "content_type": "text",
                                "parts": ["Hello, test message 1"]
                            },
                            "create_time": 1709740800
                        }
                    },
                    "msg-2": {
                        "id": "msg-2",
                        "parent": "msg-1",
                        "children": [],
                        "message": {
                            "id": "msg-2",
                            "author": {"role": "assistant"},
                            "content": {
                                "content_type": "text",
                                "parts": ["Hello, this is a response"]
                            },
                            "create_time": 1709741000,
                            "metadata": {
                                "attachments": [
                                    {
                                        "id": "file-test-1",
                                        "name": "test_image.webp",
                                        "mimeType": "image/webp"
                                    }
                                ]
                            }
                        }
                    }
                },
                "default_model_slug": "test-model"
            },
            {
                "conversation_id": "test-conv-2",
                "title": "Test Conversation 2",
                "create_time": 1709913600,  # March 2024
                "mapping": {
                    "msg-3": {
                        "id": "msg-3",
                        "parent": None,
                        "children": [],
                        "message": {
                            "id": "msg-3",
                            "author": {"role": "user"},
                            "content": {
                                "content_type": "text",
                                "parts": ["This is a different conversation"]
                            },
                            "create_time": 1709913600
                        }
                    }
                }
            }
        ]
        
        # Create a test image file
        test_image_data = b"fake image data"
        
        # Create ZIP file with test data
        with zipfile.ZipFile(self.zip_path, 'w') as zipf:
            # Add conversations.json
            zipf.writestr('conversations.json', json.dumps(conversations_data))
            
            # Add test image
            zipf.writestr('dalle-generations/file-test-1.webp', test_image_data)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_init_with_nonexistent_file(self):
        """Test initialization with a nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            ArchiveAccessor("nonexistent_file.zip")
    
    def test_get_conversations(self):
        """Test retrieving conversations from the archive."""
        accessor = ArchiveAccessor(self.zip_path)
        conversations = accessor.get_conversations()
        
        self.assertEqual(len(conversations), 2)
        self.assertEqual(conversations[0]["conversation_id"], "test-conv-1")
        self.assertEqual(conversations[1]["conversation_id"], "test-conv-2")
    
    def test_get_conversation_by_id(self):
        """Test retrieving a specific conversation by ID."""
        accessor = ArchiveAccessor(self.zip_path)
        conversation = accessor.get_conversation_by_id("test-conv-1")
        
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation["title"], "Test Conversation 1")
        
        # Try with nonexistent ID
        nonexistent = accessor.get_conversation_by_id("nonexistent")
        self.assertIsNone(nonexistent)
    
    def test_get_conversation_summary(self):
        """Test getting a conversation summary."""
        accessor = ArchiveAccessor(self.zip_path)
        conversation = accessor.get_conversation_by_id("test-conv-1")
        summary = accessor.get_conversation_summary(conversation)
        
        self.assertEqual(summary["id"], "test-conv-1")
        self.assertEqual(summary["title"], "Test Conversation 1")
        self.assertEqual(summary["create_time"], 1709740800)
        self.assertEqual(summary["model"], "test-model")
        self.assertEqual(summary["message_count"], 2)
    
    def test_get_messages(self):
        """Test retrieving messages from a conversation."""
        accessor = ArchiveAccessor(self.zip_path)
        conversation = accessor.get_conversation_by_id("test-conv-1")
        messages = accessor.get_messages(conversation)
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["depth"], 0)  # Root message
        self.assertEqual(messages[1]["depth"], 1)  # Child message
        
        # Check content
        self.assertEqual(messages[0]["data"]["content"]["parts"][0], "Hello, test message 1")
        self.assertEqual(messages[1]["data"]["content"]["parts"][0], "Hello, this is a response")
    
    def test_get_media_references(self):
        """Test retrieving media references from a conversation."""
        accessor = ArchiveAccessor(self.zip_path)
        conversation = accessor.get_conversation_by_id("test-conv-1")
        media_refs = accessor.get_media_references(conversation)
        
        self.assertEqual(len(media_refs), 1)
        self.assertEqual(media_refs[0]["id"], "file-test-1")
        self.assertEqual(media_refs[0]["name"], "test_image.webp")
    
    def test_get_media_files(self):
        """Test retrieving media files from the archive."""
        accessor = ArchiveAccessor(self.zip_path)
        media_files = accessor.get_media_files()
        
        self.assertEqual(len(media_files), 1)
        self.assertTrue("file-test-1.webp" in media_files[0])
    
    def test_find_media_file_by_id(self):
        """Test finding a media file by ID."""
        accessor = ArchiveAccessor(self.zip_path)
        media_file = accessor.find_media_file_by_id("file-test-1")
        
        self.assertIsNotNone(media_file)
        self.assertTrue("file-test-1.webp" in media_file)
        
        # Try with nonexistent ID
        nonexistent = accessor.find_media_file_by_id("nonexistent")
        self.assertIsNone(nonexistent)
    
    def test_extract_media_file(self):
        """Test extracting a media file from the archive."""
        accessor = ArchiveAccessor(self.zip_path)
        media_file = accessor.find_media_file_by_id("file-test-1")
        
        # Create temp dir for extraction
        extract_dir = tempfile.mkdtemp()
        
        try:
            extracted_path = accessor.extract_media_file(media_file, extract_dir)
            
            # Verify file was extracted
            self.assertTrue(os.path.exists(extracted_path))
            
            # Clean up
            os.remove(extracted_path)
        finally:
            os.rmdir(extract_dir)
    
    def test_get_archive_stats(self):
        """Test getting archive statistics."""
        accessor = ArchiveAccessor(self.zip_path)
        stats = accessor.get_archive_stats()
        
        self.assertEqual(stats["conversations"], 2)
        self.assertEqual(stats["messages"], 3)
        self.assertEqual(stats["media_files"], 1)
        self.assertTrue(stats["archive_size"] > 0)
    
    def test_search_messages(self):
        """Test searching for messages."""
        accessor = ArchiveAccessor(self.zip_path)
        
        # Search for text that should be found
        results = accessor.search_messages("response")
        self.assertEqual(len(results), 1)
        
        # Search for text that should not be found
        results = accessor.search_messages("nonexistent text")
        self.assertEqual(len(results), 0)

if __name__ == '__main__':
    unittest.main()