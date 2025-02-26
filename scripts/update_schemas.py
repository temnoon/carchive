#!/usr/bin/env python3
"""
Script to update the MessageDetail schema to include media_items
"""

import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to schemas.py file
SCHEMAS_PATH = Path("/Users/tem/archive/carchive/src/carchive/api/schemas.py")

def update_message_detail():
    """Update the MessageDetail schema to include media_items."""
    try:
        # Read current schemas.py
        with open(SCHEMAS_PATH, "r") as file:
            content = file.read()
        
        # Define updated MessageDetail class
        old_message_detail = '''class MessageDetail(MessageBase):
    """Detailed message schema with media."""
    media: Optional[MediaBase] = None
    referenced_media: Optional[List[MediaBase]] = []'''
        
        new_message_detail = '''class MessageDetail(MessageBase):
    """Detailed message schema with media."""
    media: Optional[MediaBase] = None
    referenced_media: Optional[List[MediaBase]] = []
    media_items: Optional[List[MediaBase]] = []'''
        
        # Replace the content
        if old_message_detail in content:
            updated_content = content.replace(old_message_detail, new_message_detail)
            
            # Write back to file
            with open(SCHEMAS_PATH, "w") as file:
                file.write(updated_content)
            
            logger.info("Successfully updated MessageDetail schema")
            return True
        else:
            logger.warning("Could not find expected MessageDetail pattern in schemas.py")
            # Try manual insertion of media_items
            if "class MessageDetail(MessageBase):" in content and "media_items: Optional[List[MediaBase]]" not in content:
                logger.info("Attempting alternative insertion method...")
                lines = content.split("\n")
                updated_lines = []
                in_message_detail = False
                
                for line in lines:
                    updated_lines.append(line)
                    if "class MessageDetail(MessageBase):" in line:
                        in_message_detail = True
                    elif in_message_detail and line.strip() == "":
                        # Insert before the end of the class
                        updated_lines.insert(len(updated_lines)-1, "    media_items: Optional[List[MediaBase]] = []")
                        in_message_detail = False
                
                # Write back to file
                with open(SCHEMAS_PATH, "w") as file:
                    file.write("\n".join(updated_lines))
                
                logger.info("Successfully added media_items using alternative method")
                return True
            else:
                logger.error("Failed to update the schema, manual intervention required")
                return False
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return False

if __name__ == "__main__":
    if update_message_detail():
        logger.info("Schema update completed successfully!")
    else:
        logger.error("Schema update failed.")
        import sys
        sys.exit(1)