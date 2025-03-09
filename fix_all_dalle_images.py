import re
import os
import uuid
from pathlib import Path
from carchive.database.session import get_session
from carchive.database.models import Media, MessageMedia, Message

# Pattern to find DALL-E asset references
asset_pattern = r'\[Asset: (file-[a-zA-Z0-9]+)\]'

def create_media_record(file_id, media_dir="./media"):
    """Create a placeholder media record for a DALL-E image"""
    # Generate a UUID for the new media record
    media_id = str(uuid.uuid4())
    
    # Create a file path in the media directory
    media_path = os.path.join(media_dir, f"{media_id}.png")
    
    # Create the media directory if it doesn't exist
    os.makedirs(media_dir, exist_ok=True)
    
    # Create an empty placeholder file
    with open(media_path, 'wb') as f:
        f.write(b'')  # Empty file as placeholder
    
    # Create media record
    with get_session() as session:
        new_media = Media(
            id=media_id,
            file_path=media_path,
            media_type='image',
            original_file_id=file_id,
            original_file_name=f"{file_id}.png",
            mime_type="image/png",
            is_generated=True,
            meta_info={"source": "dalle", "placeholder": True}
        )
        session.add(new_media)
        session.commit()
        
    return media_id

def link_media_to_message(media_id, message_id):
    """Create a link between a media item and a message"""
    with get_session() as session:
        # Check if the link already exists
        existing = session.query(MessageMedia).filter_by(
            message_id=message_id, 
            media_id=media_id
        ).first()
        
        if not existing:
            # Create a new link
            link = MessageMedia(
                message_id=message_id,
                media_id=media_id,
                association_type='generated'
            )
            session.add(link)
            session.commit()
            return True
        
    return False

def process_all_dalle_assets():
    """Process all DALL-E asset references in all conversations"""
    fixed_count = 0
    
    with get_session() as session:
        # Get all messages that might contain asset references
        # Look for messages that might contain DALL-E asset references
        messages = session.query(Message).filter(
            Message.content.like('%Asset: file-%')
        ).all()
        
        print(f"Found {len(messages)} messages with potential DALL-E asset references")
        
        # Process each message
        for message in messages:
            if not message.content:
                continue
                
            # Find all asset references
            asset_matches = re.findall(asset_pattern, message.content)
            
            if asset_matches:
                print(f"Message {message.id} in conversation {message.conversation_id} has {len(asset_matches)} assets")
                
                for file_id in asset_matches:
                    # Check if media already exists
                    media = session.query(Media).filter_by(original_file_id=file_id).first()
                    
                    if not media:
                        # Create a new media record
                        print(f"Creating media record for {file_id}")
                        media_id = create_media_record(file_id)
                        
                        # Link to message
                        link_created = link_media_to_message(media_id, message.id)
                        
                        if link_created:
                            fixed_count += 1
                            print(f"Linked media {media_id} to message {message.id}")
                    else:
                        # Link existing media to message if not already linked
                        link_created = link_media_to_message(media.id, message.id)
                        
                        if link_created:
                            fixed_count += 1
                            print(f"Linked existing media {media.id} to message {message.id}")
    
    return fixed_count

if __name__ == "__main__":
    fixed = process_all_dalle_assets()
    print(f"Fixed {fixed} DALL-E asset references")