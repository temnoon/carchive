#\!/bin/bash
# Apply embedding columns directly via SQL
export PGPASSWORD=carchive_pass
psql -U carchive_app -d carchive04_db -f add_embedding_columns.sql
