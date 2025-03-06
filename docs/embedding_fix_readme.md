# Embedding System Enhancements

This document explains the changes made to fix embedding system issues and add resumption capabilities.

## Issue Fixed

The embedding system was failing with the error:
```
column "parent_message_id" of relation "embeddings" does not exist
```

This occurred because the SQLAlchemy model was expecting `parent_message_id` and `parent_chunk_id` columns in the database, but these columns did not exist in the actual database schema.

## Solution Implemented

1. **Database Schema Update**
   - Added a SQL script to add the missing columns to the embeddings table
   - Run `./apply_embedding_columns.sh` to apply these columns directly

2. **Enhanced Error Handling**
   - Added robust error handling in the embedding code
   - Implemented a fallback mechanism that stores message/chunk IDs in the meta_info field when parent columns aren't available

3. **Resume Capability**
   - Added a `--resume/--no-resume` flag to the CLI (enabled by default)
   - When resuming, the system skips messages that already have embeddings with the specified model
   - This allows interrupted embedding processes to continue where they left off

4. **Batch Processing**
   - Implemented batch processing to handle large datasets more reliably
   - Added a `--batch-size` parameter to control batch size
   - Default batch size set to 100 embeddings per batch

## Usage

To generate embeddings with resumption capability:

```bash
poetry run carchive embed all --min-word-count 7 --resume
```

This will:
1. Skip messages that already have embeddings with the specified model
2. Process messages in batches of 100
3. Allow you to continue if the process is interrupted

Additional options:
```bash
# Process with a specific batch size
poetry run carchive embed all --min-word-count 7 --batch-size 50

# Force re-processing of all messages, even those with existing embeddings
poetry run carchive embed all --min-word-count 7 --no-resume

# Include only specific roles
poetry run carchive embed all --min-word-count 7 --include-roles user --include-roles assistant
```

## Troubleshooting

If you encounter errors about missing columns:

1. Ensure you've run the SQL script to add the columns:
   ```bash
   ./apply_embedding_columns.sh
   ```

2. Check the database schema:
   ```bash
   psql -U carchive_app -d carchive04_db -c "\d embeddings"
   ```

3. If the migration fails, you can manually add the columns:
   ```sql
   ALTER TABLE embeddings ADD COLUMN parent_message_id UUID REFERENCES messages(id);
   ALTER TABLE embeddings ADD COLUMN parent_chunk_id UUID REFERENCES chunks(id);
   ```