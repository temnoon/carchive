# Embedding Storage Solutions

There are two main issues that were identified and fixed:

## 1. Vector Dimension Mismatch

The database schema had a mismatch between:
- The code, which expected 768-dimensional vectors (for nomic-embed-text model)
- The database, which was configured for 1536-dimensional vectors

This has been fixed by:
```sql
-- Drop the vector index first
DROP INDEX IF EXISTS vector_idx;

-- Update the vector dimension
ALTER TABLE embeddings ALTER COLUMN vector TYPE vector(768);

-- Recreate the index
CREATE INDEX vector_idx ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists='1000');
```

## 2. Constraint Violations

There were two issues with constraints in the embeddings table:

1. NOT NULL constraint on parent_type:
   ```sql
   ALTER TABLE embeddings ALTER COLUMN parent_type DROP NOT NULL;
   ALTER TABLE embeddings ALTER COLUMN parent_id DROP NOT NULL;
   ```

2. CHECK constraint that didn't allow 'raw_text' as a valid parent_type:
   ```sql
   -- Drop the original constraint
   ALTER TABLE embeddings DROP CONSTRAINT check_parent_type;
   
   -- Add updated constraint that includes 'raw_text'
   ALTER TABLE embeddings ADD CONSTRAINT check_parent_type
       CHECK (parent_type::text = ANY (ARRAY['conversation', 'message', 'chunk', 'media', 'raw_text']::text[]));
   ```

3. Ensuring the code always provides a valid value for parent_type:
   - For message or chunk parents: "message" or "chunk"
   - For raw text with no parent: "raw_text"

## Alternative Storage Solution

If the database issues continue, an alternative approach has been provided:

```bash
./store_embeddings_file.py --min-word-count 7
```

This script:
- Processes messages with the same criteria
- Generates embeddings
- Stores them in a JSON Lines file instead of the database
- Can be imported later once the schema issues are resolved

## How to Apply the Fix

1. Run the fix scripts:
   ```bash
   ./apply_vector_fix.sh
   ./apply_embeddings_fix.sh
   ```

2. Try running the embedding command again:
   ```bash
   poetry run carchive embed all --min-word-count 7
   ```

3. If issues persist, use the file-based approach:
   ```bash
   ./store_embeddings_file.py --min-word-count 7
   ```

## Explanation

The core issue is a schema mismatch between:
1. The SQLAlchemy model in the code
2. The actual database table schema

The fixes align these two by:
1. Updating the database schema to match the code's expectations
2. Making the code more flexible to handle different database schemas
3. Providing a fallback file-based solution if needed
