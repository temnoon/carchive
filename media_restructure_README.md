# Media Restructuring for Carchive

This document explains the media restructuring changes implemented in the carchive application to address the traceability issues with the current media file handling system.

## Background

The current system was renaming media files to UUIDs when importing from archives, which made it difficult to trace back to the original files. Our analysis confirmed that:

1. File IDs are consistent across archives
2. Chat3 is the most complete archive
3. The current system of renaming files to UUIDs was causing traceability issues

## Implementation Details

### 1. Database Changes

Added new columns to the Media table:
- `archive_source`: Stores the original archive source (chat, chat2, chat3)
- `relative_path`: Path relative to the media root directory
- `original_path`: The full original path in the source archive

Added indexes for:
- `original_file_id`: To quickly find files by their original ID
- `checksum`: To detect duplicates

### 2. New Directory Structure

```
media_new/
├── chatgpt/
│   ├── chat/
│   ├── chat2/
│   └── chat3/
└── shared/
```

- Files are stored in their respective archive directories
- Original filenames are preserved
- The structure maintains a clear organization that corresponds to the source archives

### 3. ChatGPT Adapter Changes

- Modified to preserve original filenames during import
- Updated to create a new directory structure based on archive source
- Enhanced to store complete path information in the database 

### 4. Media API Changes

- Updated to prioritize looking for files in the new structure first
- Implemented fallback mechanisms to check other archives if a file is missing
- Maintained backward compatibility for existing file paths

## Migration Process

The migration process includes:

1. Running an Alembic migration to add the new columns to the database
2. Creating the new directory structure
3. Copying files from the source archives to the new structure, preserving original filenames
4. Updating database records with new path information
5. Verifying file accessibility in the new structure

## How to Run the Migration

Execute the `apply_media_restructure.sh` script to perform the migration:

```bash
./apply_media_restructure.sh
```

The script will:
1. Run the Alembic migration to add new columns
2. Create the new directory structure
3. Run a dry-run first to analyze what needs to be migrated
4. Ask for confirmation before proceeding with the actual migration
5. Perform the migration and update database records

## Post-Migration

After migration:
1. Run the verification script to check that everything migrated correctly:
   ```bash
   source venv_310/bin/activate
   export PYTHONPATH=$PWD/src:$PYTHONPATH
   ./verify_media_restructure.py --api-url http://localhost:8000 --output migration_verification.json
   ```

2. The verification script checks:
   - Database records have been properly updated with new fields
   - Files are accessible through the API
   - Message-media associations remain intact

3. Once verification passes, update the `MEDIA_DIR` setting to point to the new structure:
   - Edit your `.env` file and set `CARCHIVE_MEDIA_DIR=media_new`
   - Or set the environment variable: `export CARCHIVE_MEDIA_DIR=media_new`

4. Restart the servers to apply the new configuration:
   ```bash
   carchive server stop
   carchive server start-all
   ```

## Rollback Plan

If issues arise:
1. Restore the original database backup
2. Keep using the original media directory
3. Disable the new columns in the API routes

The migration maintains backward compatibility, so rolling back is primarily a matter of reverting to use the original database and media directory.

## Verification Queries

To verify the migration, you can run these SQL queries:

```sql
-- Check how many media records have been migrated
SELECT COUNT(*) FROM media WHERE archive_source IS NOT NULL;

-- Check distribution across archives
SELECT archive_source, COUNT(*) FROM media GROUP BY archive_source;

-- Find any media that failed to migrate
SELECT id, file_path FROM media WHERE archive_source IS NULL;
```