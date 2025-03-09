import json
from carchive.database.session import get_session
from carchive.database.models import Conversation, Message, MessageMedia, Media

conversation_id = 'e91bf5d0-0030-4f6e-af17-2d57f1da9392'

with get_session() as session:
    # Check if conversation exists
    conv = session.query(Conversation).filter_by(id=conversation_id).first()
    print(f'Conversation: {conv.title if conv else None}')
    
    if conv:
        # Get media associations for messages in this conversation
        media_assoc = session.query(MessageMedia).join(
            Message, Message.id == MessageMedia.message_id
        ).filter(
            Message.conversation_id == conversation_id
        ).all()
        
        print(f'Media associations: {len(media_assoc) if media_assoc else 0}')
        
        # Get details about each media association
        for assoc in media_assoc:
            media = session.query(Media).filter_by(id=assoc.media_id).first()
            message = session.query(Message).filter_by(id=assoc.message_id).first()
            
            if media and message:
                print(f'Media ID: {media.id}')
                print(f'  Original file: {media.original_file_name}')
                print(f'  Original file ID: {media.original_file_id}')
                print(f'  File path: {media.file_path}')
                print(f'  Media type: {media.media_type}')
                print(f'  Associated with message: {message.id} (role: {message.role})')
                print(f'  Message content preview: {message.content[:100]}...')
                print('-' * 50)