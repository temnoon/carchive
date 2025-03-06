#\!/bin/bash
# Fix the constraint on parent_type to allow raw_text
export PGPASSWORD=carchive_pass
psql -U carchive_app -d carchive04_db -f fix_parent_type_constraint.sql
