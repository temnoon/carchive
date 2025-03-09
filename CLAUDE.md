# CLAUDE.md - carchive Development Guide

  ## Carchive Architecture Standards

  ### Technology Stack Standards
  - **Web Framework**: Flask for both API and GUI (standardized)
  - **Type Validation**: Pydantic with flask-pydantic integration
  - **Database ORM**: SQLAlchemy with explicit session management
  - **CLI Framework**: Typer for command-line interfaces
  - **Environment Management**: Poetry for dependency management

  ### Directory Structure Standards
  - Full Path to project directory from local filesystem root:
  - '/Users/tem/archive/carchive/'
  Relative paths from project directory:
  - `/src/carchive/`: Main application code
    - `/agents/`: Agent implementations
    - `/api/`: API server (Flask)
    - `/gui/`: Web interface (Flask)
    - `/database/`: Models and connection handling
    - `/cli/`: Command-line tools
    - `/utils/`: Shared utilities
    - `/schemas/`: Pydantic models
    - `/scripts/`: Core utility scripts used by components
  - `/scripts/`: One-off utility scripts (should be minimal)
  - Root project directory: Essential entry points, environment setup, source data archives and expanded archives.

  ### Code Standards
  1. **Flask Integration**:
     - Use Flask for all web serving (API and GUI)
     - Use blueprints for route organization
     - Explicitly handle database sessions

  2. **Pydantic Usage**:
     - Define schemas in `/src/carchive/schemas/`
     - Use `flask-pydantic` for request/response validation
     - Enable `orm_mode=True` for easy conversion from SQLAlchemy
     - Use `validate_arguments` decorator for internal function validation

  3. **Database Patterns**:
     - Use context managers for sessions (`with get_session() as session:`)
     - Define explicit relationships in SQLAlchemy models
     - Validate inputs before database operations

  4. **Error Handling**:
     - Use custom exception classes
     - Return consistent error structures in API responses
     - Log errors with appropriate levels (warning, error, etc.)

  5. **CLI Commands**:
     - Use `server_cli.py` for all server management
     - Structure commands in logical hierarchy
     - Provide clear help text

  ### Server Management
  - All servers run on 8000 (API) and 8001 (GUI) ports
  - Server management happens exclusively through CLI
  - Example: `poetry run carchive server start-all`
  - Avoid direct use of Flask's development server in production

  ### Standard Workflow
  1. Activate the Python environment (preferably Python 3.10):
     ```bash
     # If using venv_310 (recommended)
     source venv_310/bin/activate

     # Set PYTHONPATH
     export PYTHONPATH=$PWD/src:$PYTHONPATH
     ```

  2. Check server status:
     ```bash
     carchive server status
     ```

  3. Start both servers:
     ```bash
     carchive server start-all
     ```

  4. Stop servers when done:
     ```bash
     carchive server stop
     ```

  5. When making changes to CLI commands, test with:
     ```bash
     # Run a single command
     python -m carchive.cli.main_cli server status
     ```

  ### Migration Plan
  1. Retire all code related to ports 5000/5001
  2. Convert FastAPI routes to Flask with Pydantic validation
  3. Consolidate script organization
  4. Remove all "carchive2" references
  5. Standardize on Flask+Pydantic patterns

  ### Naming Standards
  - Project name is "carchive" (never "carchive2")
  - Use consistent naming across all components
  - File names should reflect purpose (e.g., `conversation_service.py`)

  ### Development Workflow
  - Development happens on feature branches
  - Tests must pass before merging
  - CLI commands for environment setup and testing


---


## Build and Run Commands
- Setup: `poetry install`
- Run CLI: `poetry run carchive`
- Run single test: `poetry run pytest tests/test_filename.py::test_function_name -v`
- Run all tests: `poetry run pytest`
- Add dependency: `poetry add package_name`
- Create new database: `./setup_carchive04_db.sh`
- Migrate ChatGPT archive: `poetry run carchive migrate chatgpt chat2/conversations.json`
- Start servers: `poetry run carchive server start-all --api-port 8000 --gui-port 8001`
- Stop servers: `poetry run carchive server stop`
- Server status: `poetry run carchive server status`
- Reset media records: `python reset_media_db.py`
- Import media from chat3: `python import_chat3_media.py --source-dir chat3 --target-dir media_new`
- Run media restructure script: `./apply_chat3_media_import.sh` (combines reset and import)

## Media CLI Commands
- Media analysis: `poetry run carchive media analyze-media-distribution`
- Find media: `poetry run carchive media find --media-type image --limit 10`
- Find conversations with media: `poetry run carchive media find-conversations --media-type image --limit 10`
- Link AI-generated images: `poetry run carchive media link-ai-generated-images`
- Media restructuring: `poetry run carchive media restructure --source-dirs chat chat2 chat3 --target-dir media_new --no-dry-run`

---

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
- **Validation**: Use Pydantic models for request/response validation
- **API Routes**: Use flask-pydantic for endpoint validation
- **Schemas**: Define Pydantic models with orm_mode=True for ORM compatibility
- **Database Access**: Always use context managers for session handling:
  ```python
  with get_session() as session:
      # database operations
  ```
---


## PostgreSQL and pgvector
  This project uses PostgreSQL with pgvector for vector embeddings, requiring proper database setup.

  Initial setup requires PostgreSQL 13+ with pgvector extension. Configure connection settings in:
  - `.env` file (for development)
  - Environment variables (for production)
  - Command-line parameters (for one-off operations)

  Connection string template: `postgresql://carchive_app:carchive_pass@localhost:5432/carchive04_db`
  For development work when the current state of the database tables needs to be checked, use the 'postgres' postgreSQL user, to have simple access to all tables, data and priviledges from the context of the development user account.
---


## Important Implementation Details

### LaTeX Rendering
The project supports rendering LaTeX math notation in conversations. A working implementation
that correctly handles both inline and display math is preserved in:
`docs/working_latex_renderer_backup.py`

This file should be used as a reference when troubleshooting LaTeX rendering issues. The key features:
- Converts square bracket notation `[...]` to display math in preprocessing
- Uses dollar sign notation for LaTeX during intermediate processing
- Handles nested delimiters to prevent displaying red text like `\(` and `\)`
- Post-processes HTML to ensure proper rendering of math blocks

When adjusting LaTeX rendering, be careful not to break the following:
1. Inline LaTeX expressions (within text)
2. Display math using square brackets on separate lines
3. LaTeX environments like align, equation, etc.
4. Reference numbers in square brackets (should not be treated as math)

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

 ### Server Architecture
  - API server runs on port 8000 using Flask with Pydantic validation
  - GUI server runs on port 8001 using Flask templates
  - Server management happens through the CLI interface
  - Configuration is passed through environment variables or CLI parameters
  - The `server_cli.py` provides programmatic access to server management

---

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

---

## ChatGPT Migration Process

### Setup and Initial Migration
1. Set up the database: `poetry run carchive db setup`
2. Migrate ChatGPT archives: `poetry run carchive migrate chatgpt path/to/conversations.json`
3. Media handling is automatic through the CLI

---


 ## Media Handling

  ### Storage Structure
  Media files are now stored in a structured directory hierarchy:
  - Base path: `./media_new/`
  - Organized hierarchically by provider and archive source:
    ```
    media_new/
    ├── chatgpt/
    │   ├── chat/     # Files from the chat archive
    │   ├── chat2/    # Files from the chat2 archive
    │   └── chat3/    # Files from the chat3 archive (most complete)
    └── shared/       # Shared files across archives
    ```
  - Original filenames are preserved (no longer renamed to UUIDs)
  - Original paths and checksums stored in database
  - Access through API endpoints: `/api/media/{media_id}`

  ### Media Table Structure
  The `media` table has been enhanced with additional columns:
  - `archive_source`: Stores the original archive source (chat, chat2, chat3)
  - `relative_path`: Path relative to the media root directory
  - `original_path`: The full original path in the source archive
  - `checksum`: MD5 checksum for file verification and deduplication

  Additional indexes have been added for:
  - `original_file_id`: To quickly find files by their original ID
  - `checksum`: To detect duplicates

  ### Media Processing
  - Original filenames preserved during import
  - Thumbnails generated for images
  - PDF previews created for documents
  - Links established between messages and media through `message_media` table
  - DALL-E images properly associated with their generating messages
  - Robust file lookups with fallbacks to other archives if a file is missing

The media files in ChatGPT exports follow a naming convention:
```
file-{ID}-{original_filename}
```

Where the ID is not exactly the same as the attachment ID in the JSON, but contains it. The migration adapter uses flexible matching to find the correct file:
1. First tries an exact match with the full attachment ID
2. If that fails, it tries matching by the first 8 characters of the ID
3. When a match is found, it copies the file to the new directory structure preserving the original filename

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

---

## Server Configuration

  ### Default Ports
  - API server: 8000
  - GUI server: 8001

  ### Environment Variables
  - `CARCHIVE_DB_URI`: Database connection string
  - `CARCHIVE_MEDIA_DIR`: Media storage directory (set to `media_new` for the restructured media)
  - `CARCHIVE_API_URL`: URL for API (used by GUI)
  - `FLASK_DEBUG`: Enable debug mode (1) or disable (0)
  - `CARCHIVE_CORS_ENABLED`: Enable CORS support

  ### Configuration Precedence
  1. Command-line arguments
  2. Environment variables
  3. Configuration files
  4. Default values

---


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
```

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

---
