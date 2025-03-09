#!/usr/bin/env python3
"""Debug script for archive functionality."""

import sys
import json
import traceback
from pathlib import Path

from carchive.archive.archive_accessor import ArchiveAccessor

def debug_archive(archive_path):
    """Run a debug check of archive processing."""
    print(f"DEBUG: Starting debug of archive: {archive_path}")
    
    try:
        # Try to create the accessor
        print("DEBUG: Creating ArchiveAccessor...")
        accessor = ArchiveAccessor(str(archive_path))
        print("DEBUG: ArchiveAccessor created successfully")
        
        # Get media mapping
        print("DEBUG: Calling get_media_mapping()...")
        try:
            media_mapping = accessor.get_media_mapping()
            print(f"DEBUG: get_media_mapping() returned {len(media_mapping)} items")
            
            # Check structure of first few items
            print("\nDEBUG: First few media mapping items:")
            for i, item in enumerate(media_mapping[:3]):
                print(f"\nItem {i+1}:")
                print(f"  Keys: {list(item.keys())}")
                print(f"  path: {item.get('path')}")
                print(f"  filename: {item.get('filename')}")
                print(f"  file_id: {item.get('file_id')}")
                print(f"  references: {len(item.get('references', []))} entries")
                
                # Check the first reference
                if item.get('references') and len(item.get('references', [])) > 0:
                    ref = item['references'][0]
                    if ref:
                        print(f"    First reference keys: {list(ref.keys())}")
                    else:
                        print("    First reference is None")
            
        except Exception as e:
            print(f"DEBUG ERROR: Failed in get_media_mapping(): {str(e)}")
            traceback.print_exc()
            return
        
        # Test filtering
        print("\nDEBUG: Testing role filtering...")
        try:
            # Filter for tool messages (most likely to be DALL-E)
            tool_items = []
            for item in media_mapping:
                if not item or not isinstance(item, dict) or 'references' not in item:
                    continue
                    
                matching_refs = []
                for ref in item.get('references', []):
                    if ref and isinstance(ref, dict) and ref.get('role') == 'tool':
                        matching_refs.append(ref)
                
                if matching_refs:
                    try:
                        new_item = item.copy()
                        new_item['references'] = matching_refs
                        tool_items.append(new_item)
                    except (TypeError, AttributeError) as err:
                        print(f"DEBUG ERROR: Failed to copy item: {err}")
            
            print(f"DEBUG: Found {len(tool_items)} items with tool role")
        except Exception as e:
            print(f"DEBUG ERROR: Failed in role filtering: {str(e)}")
            traceback.print_exc()
            return
        
        # Test type filtering
        print("\nDEBUG: Testing type filtering...")
        try:
            # Filter for generated images
            generated_items = []
            for item in tool_items:
                if not item or not isinstance(item, dict) or 'path' not in item:
                    continue
                    
                path = item.get('path', '')
                if not path or not isinstance(path, str):
                    continue
                    
                if 'dalle-generations' in path or path.endswith('.webp'):
                    generated_items.append(item)
            
            print(f"DEBUG: Found {len(generated_items)} generated image items")
        except Exception as e:
            print(f"DEBUG ERROR: Failed in type filtering: {str(e)}")
            traceback.print_exc()
            return
        
        # Test CSV formatting
        print("\nDEBUG: Testing CSV formatting...")
        try:
            print("Converting first 10 items to CSV format...")
            flattened_data = []
            
            for item in generated_items[:10]:
                if not item.get('references'):
                    print(f"Item has no references: {item}")
                    continue
                
                for ref in item.get('references', []):
                    if not ref or not isinstance(ref, dict):
                        print(f"Reference is not valid: {ref}")
                        continue
                    
                    # Create safe data with defaults for all fields
                    safe_data = {
                        'path': item.get('path', ''),
                        'filename': item.get('filename', ''),
                        'file_id': item.get('file_id', ''),
                        'conversation_id': '',
                        'message_id': '',
                        'role': '',
                        'assistant_parent_id': '',
                        'file_name': '',
                        'mime_type': ''
                    }
                    
                    # Safely add reference data
                    if ref:
                        if isinstance(ref.get('conversation_id'), str):
                            safe_data['conversation_id'] = ref.get('conversation_id', '')
                        if isinstance(ref.get('message_id'), str):
                            safe_data['message_id'] = ref.get('message_id', '')
                        if isinstance(ref.get('role'), str):
                            safe_data['role'] = ref.get('role', '')
                        if isinstance(ref.get('file_name'), str):
                            safe_data['file_name'] = ref.get('file_name', '')
                        if isinstance(ref.get('mime_type'), str):
                            safe_data['mime_type'] = ref.get('mime_type', '')
                        
                        # Handle assistant_parent_id with extra care
                        assistant_msg_id = ref.get('assistant_parent_id', '')
                        if assistant_msg_id is None:
                            assistant_msg_id = ''
                        if ref.get('role') == 'user':
                            assistant_msg_id = ''
                        safe_data['assistant_parent_id'] = assistant_msg_id
                    
                    flattened_data.append(safe_data)
            
            print(f"DEBUG: Created {len(flattened_data)} flattened records")
            
            if flattened_data:
                # Print first record for inspection
                print(f"DEBUG: First CSV record: {json.dumps(flattened_data[0], indent=2)}")
            
        except Exception as e:
            print(f"DEBUG ERROR: Failed in CSV formatting: {str(e)}")
            traceback.print_exc()
            return
            
        print("\nDEBUG: All tests completed successfully!")
        
    except Exception as e:
        print(f"DEBUG ERROR: Unexpected failure: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_archive_cli.py <archive_path>")
        sys.exit(1)
    
    archive_path = Path(sys.argv[1])
    if not archive_path.exists():
        print(f"Error: Archive file '{archive_path}' not found")
        sys.exit(1)
    
    debug_archive(archive_path)