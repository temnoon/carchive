import os
import re
import json
import requests
from carchive.database.session import get_session
from carchive.database.models import Message, Media, MessageMedia

# Constants
CONVERSATION_ID = 'e91bf5d0-0030-4f6e-af17-2d57f1da9392'
API_URL = 'http://127.0.0.1:8000'

# Regular expressions to match file references
asset_pattern = r'\[Asset: (file-[a-zA-Z0-9]+)\]'
file_id_pattern = r'\b(file-[a-zA-Z0-9]+)\b'

def trace_message_processing(message):
    """Trace the message processing with detailed diagnostics"""
    print(f"\n===== Processing Message ID: {message.id} =====")
    print(f"Role: {message.role}")
    print(f"Content (first 100 chars): {message.content[:100] if message.content else 'None'}...")
    
    # Check for media associations
    media_assocs = []
    with get_session() as session:
        media_assocs = session.query(MessageMedia).filter_by(message_id=message.id).all()
        
    print(f"Media associations in database: {len(media_assocs)}")
    
    for assoc in media_assocs:
        with get_session() as session:
            media = session.query(Media).filter_by(id=assoc.media_id).first()
            if media:
                print(f"  Media ID: {media.id}")
                print(f"  Original file: {media.original_file_name}")
                print(f"  Original file ID: {media.original_file_id}")
                print(f"  File path: {media.file_path}")
                print(f"  Media type: {media.media_type}")
                print(f"  File exists: {os.path.exists(media.file_path)}")
    
    # Check content for asset references
    if message.content:
        asset_matches = re.findall(asset_pattern, message.content)
        file_matches = re.findall(file_id_pattern, message.content)
        
        if asset_matches:
            print(f"Asset references in content: {asset_matches}")
            
            # Look for these file IDs in the media table
            for file_id in asset_matches:
                with get_session() as session:
                    media = session.query(Media).filter_by(original_file_id=file_id).first()
                    if media:
                        print(f"  Found media for {file_id}: {media.id}")
                        print(f"  Media file exists: {os.path.exists(media.file_path)}")
                    else:
                        # Check if there's anything that partially matches
                        partial_matches = session.query(Media).filter(
                            Media.original_file_id.like(f"%{file_id[:8]}%")
                        ).all()
                        
                        if partial_matches:
                            print(f"  Partial matches for {file_id}:")
                            for m in partial_matches:
                                print(f"    {m.id}: {m.original_file_id}")
                        else:
                            print(f"  No media found for {file_id}")
                            
                            # Check if there's anything in the actual media directory
                            media_dir = './media'
                            if os.path.exists(media_dir):
                                matching_files = [f for f in os.listdir(media_dir) if file_id in f]
                                if matching_files:
                                    print(f"  Files in media directory matching {file_id}: {matching_files}")
        
        if file_matches and set(file_matches) != set(asset_matches):
            print(f"Additional file ID references in content: {set(file_matches) - set(asset_matches)}")

def simulate_api_request():
    """Simulate the API request that the GUI makes"""
    try:
        # Request conversation data from API
        api_endpoint = f"{API_URL}/api/conversations/{CONVERSATION_ID}"
        params = {
            'include_messages': 'true',
            'page': 1,
            'per_page': 50
        }
        
        response = requests.get(api_endpoint, params=params, timeout=15)
        status_code = response.status_code
        
        print(f"API Response status code: {status_code}")
        
        if status_code == 200:
            # Process the response
            data = response.json()
            print(f"Conversation title: {data.get('title', 'Unknown')}")
            messages = data.get('messages', [])
            print(f"Message count: {len(messages)}")
            
            # Check messages for media info
            for idx, message in enumerate(messages):
                print(f"\nMessage {idx+1} (ID: {message.get('id')})")
                print(f"Role: {message.get('role')}")
                
                # Check for media items
                media_items = message.get('media_items', [])
                if media_items:
                    print(f"Media items: {len(media_items)}")
                    for item in media_items:
                        print(f"  Media ID: {item.get('id')}")
                        print(f"  Media type: {item.get('media_type')}")
                
                # Check for single media item
                media = message.get('media')
                if media and isinstance(media, dict):
                    print(f"Single media item: {media.get('id')}")
                
                # Check content for DALL-E references
                content = message.get('content', '')
                if isinstance(content, str) and 'Asset: file-' in content:
                    print(f"Contains DALL-E asset reference")
                    file_ids = re.findall(asset_pattern, content)
                    print(f"  File IDs: {file_ids}")
        else:
            print(f"Error response: {response.text}")
    except Exception as e:
        print(f"Error making API request: {str(e)}")
        
def examine_database_schema():
    """Check the actual database schema for media and message_media tables"""
    with get_session() as session:
        try:
            # Check media table schema
            media_columns = session.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'media'").fetchall()
            print("\n===== Media Table Schema =====")
            for col in media_columns:
                print(f"{col[0]}: {col[1]}")
                
            # Check message_media table schema
            mm_columns = session.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'message_media'").fetchall()
            print("\n===== MessageMedia Table Schema =====")
            for col in mm_columns:
                print(f"{col[0]}: {col[1]}")
                
            # Check if there are any constraints or indices missing
            constraints = session.execute("SELECT * FROM information_schema.constraint_column_usage WHERE table_name IN ('media', 'message_media')").fetchall()
            print("\n===== Table Constraints =====")
            for constraint in constraints:
                print(constraint)
        except Exception as e:
            print(f"Error examining schema: {str(e)}")

def main():
    """Run all diagnostic functions"""
    print("===== Starting Media Handling Diagnostics =====")
    
    # First examine the actual schema
    examine_database_schema()
    
    # Get all messages for the conversation
    with get_session() as session:
        messages = session.query(Message).filter_by(conversation_id=CONVERSATION_ID).order_by(Message.created_at).all()
        print(f"\nFound {len(messages)} messages in conversation")
        
        # Process each message
        for message in messages:
            trace_message_processing(message)
    
    # Simulate the API request
    print("\n===== Simulating API Request =====")
    simulate_api_request()
    
    print("\n===== Diagnostics Complete =====")

if __name__ == "__main__":
    main()