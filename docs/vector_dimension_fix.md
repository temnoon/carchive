# Vector Dimension Fix

## Issue

The system was encountering a vector dimension mismatch error:
```
expected 1536 dimensions, not 768
```

This occurred because:
1. The model definition in SQLAlchemy correctly specified Vector(768)
2. But the actual database table had vector columns with a dimension of 1536
3. When inserting 768-dimensional vectors from nomic-embed-text, this caused a dimension mismatch error

## Solution

1. Modified the database schema to use 768 dimensions:
   ```sql
   ALTER TABLE embeddings ALTER COLUMN vector TYPE vector(768);
   ```

2. Verified the model definition correctly uses 768 dimensions:
   ```python
   vector = Column(Vector(768))  # Using 768 dimensions for nomic-embed-text model
   ```

3. Added a script to apply the fix:
   - `apply_vector_fix.sh` - Uses SQL to alter the vector column dimension

## How to Apply

1. Run the fix script:
   ```bash
   ./apply_vector_fix.sh
   ```

2. Verify the fix was applied:
   ```bash
   psql -U carchive_app -d carchive04_db -c "SELECT vector_dims(vector) FROM embeddings LIMIT 1;"
   ```
   This should return 768.

3. Continue with embedding:
   ```bash
   poetry run carchive embed all --min-word-count 7
   ```

## Technical Details

The pgvector extension in PostgreSQL requires vector dimensions to match when inserting data.
The ollama model with nomic-embed-text produces 768-dimensional vectors, so the database schema
needs to match this dimension exactly.
