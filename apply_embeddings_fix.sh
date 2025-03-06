#\!/bin/bash
# Fix the embeddings table to make parent_type and parent_id nullable
export PGPASSWORD=carchive_pass
psql -U carchive_app -d carchive04_db -f fix_embeddings_table.sql
