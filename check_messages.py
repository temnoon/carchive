import json
import re
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, MessageMedia, Media

conversation_id = 'e91bf5d0-0030-4f6e-af17-2d57f1da9392'

asset_pattern = r'\[Asset: (file-[a-zA-Z0-9]+)\]'
file_id_pattern = r'\b(file-[a-zA-Z0-9]+)\b'

with get_session() as session:
    # Get messages for this conversation
    messages = session.query(Message).filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
    
    print(f'Total messages: {len(messages)}')
    
    for message in messages:
        print(f'Message ID: {message.id}')
        print(f'  Role: {message.role}')
        print(f'  Content preview: {message.content[:100] if message.content else "None"}...')
        
        # Check for asset references
        if message.content:
            asset_matches = re.findall(asset_pattern, message.content)
            file_matches = re.findall(file_id_pattern, message.content)
            
            if asset_matches:
                print(f'  Asset references found: {asset_matches}')
                
                # Look up these assets in the media table
                for asset_id in asset_matches:
                    media = session.query(Media).filter_by(original_file_id=asset_id).first()
                    if media:
                        print(f'    Found media for {asset_id}: {media.id}, {media.media_type}, {media.file_path}')
                    else:
                        print(f'    No media found for {asset_id}')
            
            if file_matches and not asset_matches:  # Only show if different from asset_matches
                print(f'  File ID references found: {file_matches}')
                
                # Look up these files in the media table
                for file_id in file_matches:
                    media = session.query(Media).filter_by(original_file_id=file_id).first()
                    if media:
                        print(f'    Found media for {file_id}: {media.id}, {media.media_type}, {media.file_path}')
                    else:
                        print(f'    No media found for {file_id}')
                        
        # Check if message metadata has attachments
        if message.meta_info and isinstance(message.meta_info, dict):
            if 'attachments' in message.meta_info:
                print(f'  Attachments in metadata: {message.meta_info["attachments"]}')
        
        print('-' * 50)