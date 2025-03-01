# CLAUDE.md - carchive Development Guide

## Build and Run Commands
- Setup: `poetry install`
- Run CLI: `poetry run carchive`
- Run single test: `poetry run pytest tests/test_filename.py::test_function_name -v`
- Run all tests: `poetry run pytest`
- Add dependency: `poetry add package_name`
- Create new database: `./setup_carchive04_db.sh`
- Migrate ChatGPT archive: `poetry run carchive migrate chatgpt chat2/conversations.json`

## Code Style Guidelines
- **Structure**: Follow modular design with core/, database/, agents/, etc. folders
- **Imports**: Group stdlib, then third-party, then local imports with a blank line between groups
- **Types**: Use type hints for function parameters and return values
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Docstrings**: Include docstrings for all modules, classes, and functions (triple quotes)
- **Error handling**: Use specific exceptions with informative messages
- **SQLAlchemy**: Follow established patterns for models with descriptive relationships
- **CLI**: Implement with Typer, with clear help text and logical command structure
- **Testing**: Test files should be in tests/ directory with clear test_* naming

## PostgreSQL and pgvector
This project uses PostgreSQL with pgvector for vector embeddings, requiring proper database setup.

## Important Implementation Details

### Conversation Timestamps
Conversations can have timestamps in multiple formats:
1. Explicit `create_time` and `update_time` fields in meta_info (as Unix timestamps)
2. For older conversations without these fields, the timestamps in the messages table are authoritative
   - First message timestamp = conversation creation time
   - Last message timestamp = conversation update time
3. If neither of the above are available, the database's `created_at` field is used as a fallback

The service implementations in conversation_service.py inject these timestamps into ConversationRead
objects at runtime using `_first_message_time` and `_last_message_time` attributes.

IMPORTANT NOTES:
- When migrating from conversations.json, the original timestamps must be preserved in the meta_info field
- The meta_info column is of type `json`, not `jsonb`. This requires special handling when updating JSON fields
- To fix timestamps, use SQL with jsonb_build_object:
  ```sql
  UPDATE conversations
  SET meta_info = jsonb_build_object(
      'source_conversation_id', meta_info->>'source_conversation_id',
      'is_anonymous', meta_info->>'is_anonymous',
      'create_time', 1234567890.123, -- Unix timestamp from conversations.json
      'update_time', 1234567890.456  -- Unix timestamp from conversations.json
  )
  WHERE id = 'conversation-uuid';
  ```
- When accessing timestamps in meta_info, always use get() rather than direct key access:
  ```python
  if meta_info and meta_info.get('create_time'):
      timestamp = float(meta_info['create_time'])
  ```

NOTE: The approach of extracting timestamps from the first 8 characters of `source_conversation_id` as
a hexadecimal Unix timestamp was attempted but found to be unreliable, producing dates far in the future for
older conversations.

# Important Details for Working with Chat Archives

## Carchive04 Database Structure
The new carchive04_db is designed for multi-provider imports with improved data organization:

### Key Tables
- **providers**: Information about different chat providers (ChatGPT, Claude, etc.)
- **conversations**: Main conversation metadata with enhanced timestamp handling
- **messages**: Message content with proper parent-child relationships
- **message_relations**: Explicit tree structure for message threads
- **media**: Improved media file tracking with checksums
- **message_media**: Links messages to their media attachments
- **chunks**: Message segments for fine-grained search
- **embeddings**: Vector embeddings with support for multiple granularities
- **collections/collection_items**: For organizing content
- **tags/tagged_items**: For flexible labeling of content

### Improvements
- Normalized schema with preservation of original metadata
- Explicit parent-child relationships for messages
- Better timestamp handling with multiple sources
- Enhanced media management with checksums
- Support for multiple vector embedding types and dimensions
- Tagged and collection-based organization

## ChatGPT Migration Process

### Setup and Initial Migration
1. Run `./setup_carchive04_db.sh` to create the database
2. Use `poetry run carchive migrate chatgpt --db-name=carchive04_db --db-user=carchive_app --db-password=carchive_pass chat2/conversations.json` for ChatGPT archives
3. Media files are copied to a structured directory and linked in the database

### Media File Handling
The media files in ChatGPT exports follow a naming convention:
```
file-{ID}-{original_filename}
```

Where the ID is not exactly the same as the attachment ID in the JSON, but contains it. The migration adapter uses flexible matching to find the correct file:
1. First tries an exact match with the full attachment ID
2. If that fails, it tries matching by the first 8 characters of the ID
3. When a match is found, it copies the file to the media directory with a UUID-based name

### Handling Different Content Types
ChatGPT exports contain various message content types, handled as follows:

- **Text**: Simple text messages
- **Code**: Code blocks
- **Multimodal Text**: Complex messages that may contain:
  - Text parts
  - Image references (handled through media files)
  - Audio assets (transcriptions preserved in text)
  - File attachments

### Provider System
The import system now uses a provider-based architecture for different chat platforms:
- Provider ID for ChatGPT: `11111111-1111-1111-1111-111111111111`
- Provider ID for Claude: `22222222-2222-2222-2222-222222222222`
- Provider ID for Perplexity: `33333333-3333-3333-3333-333333333333`

### Migration CLI Usage
```bash
# Basic usage
poetry run carchive migrate chatgpt path/to/conversations.json

# With explicit database parameters
poetry run carchive migrate chatgpt --db-name=mydb --db-user=myuser --db-password=mypass path/to/conversations.json

# With custom media directories
poetry run carchive migrate chatgpt --media-dir=path/to/media --target-media-dir=path/to/destination path/to/conversations.json
```

## ChatGPT Archive Format Notes

  ### Tools and Database Access
  - Use `jq` CLI tool for examining JSON files (e.g., `jq '.' conversations.json | head -100`)
  - Use `psql` for PostgreSQL database access
  - Database owner (with all privileges): `carchive_app`
  - Database superuser (for convenience): `postgres`

  ### Conversations.json Structure
  The ChatGPT archive exports include a main `conversations.json` file with this structure:

  ```json
  [
    {
      "conversation_id": "67bdd9b3-6888-8005-a3b2-05a9e8b0b51a",
      "title": "Conversation Title",
      "create_time": 1740495283.644186,  // Unix timestamp
      "update_time": 1740497646.418124,  // Unix timestamp
      "current_node": "node-id",
      "mapping": {
        "message-id-1": {
          "id": "message-id-1",
          "children": ["message-id-2"],
          "parent": null,
          "message": {
            "id": "message-id-1",
            "author": {
              "role": "user",  // Also: "assistant", "system", "tool"
              "name": null,
              "metadata": {}
            },
            "create_time": 1740495283.6492,  // Unix timestamp
            "update_time": null,
            "content": {
              "content_type": "text",  // Also: "code", "multimodal_text", etc.
              "parts": ["Message content here"]
            },
            "status": "finished_successfully",
            "metadata": {
              // May contain attachments and other data
              "attachments": [
                {
                  "id": "file-id",
                  "name": "filename.pdf",
                  "mimeType": "application/pdf",
                  "fileSizeTokens": 12345
                }
              ]
            }
          }
        }
        // More messages...
      },
      // Other conversation metadata...
      "moderation_results": [],
      "default_model_slug": "gpt-4o",
      "plugin_ids": [],
      "conversation_template_id": null,
      "gizmo_id": null,
      "gizmo_type": null,
      "is_archived": false,
      "is_starred": null
    }
    // More conversations...
  ]

  Timestamp Handling

  Conversations can have timestamps in multiple formats:
  1. Explicit create_time and update_time fields at conversation level (as Unix timestamps)
  2. For inconsistent timestamps, the message timestamps should be used as fallback:
    - First message timestamp = conversation creation time
    - Last message timestamp = conversation update time
  3. Implementation recommendations:
    - For conversation create_time: Use original timestamp by default, fallback to first message timestamp when discrepancy exceeds 60 seconds
    - For conversation update_time: Consider using last message timestamp as the source of truth, storing original in metadata
    - Store original timestamps in meta_info JSONB for reference

  Message Structure

  - Messages live in the mapping object, keyed by message ID
  - Each message has parent-child relationships for threading
  - Important message fields:
    - author.role: Identifies message source ("user", "assistant", "system", "tool")
    - content.content_type: Format of the message ("text", "code", "multimodal_text", etc.)
    - content.parts: Array containing the actual message content
    - metadata: Contains attachments and other message-specific data

  Attachments Handling

  - Attachments are stored in message.metadata.attachments array
  - Each attachment has: id, name, mimeType, fileSizeTokens
  - The actual files are stored separately in the archive
  - Consider moving files to a standardized directory structure while preserving paths in DB

  Examining archives with jq

  Useful jq commands:
  # Count conversations
  jq 'length' conversations.json

  # View basic conversation info
  jq 'limit(5; .[]) | {id: .conversation_id, title, create_time}' conversations.json

  # Check timestamp distribution
  jq -r 'map(.create_time) | sort | [.[0], .[length-1]] | map(todate) | join(" to ")' conversations.json

  # Find conversations with specific issues
  jq -r 'map(select(.title | contains("specific term")))' conversations.json
