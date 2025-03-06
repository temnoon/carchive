#\!/bin/bash
# Fix the vector dimension in the database
export PGPASSWORD=carchive_pass
psql -U carchive_app -d carchive04_db -f fix_vector_dimension.sql
