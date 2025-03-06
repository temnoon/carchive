#\!/bin/bash
# Apply all fixes and run the embedding command

# Apply the vector dimension fix
./apply_vector_fix.sh

# Apply the constraints fix for parent_type/parent_id
./apply_embeddings_fix.sh

# Apply the constraint fix for raw_text
./apply_constraint_fix.sh

# Run the embedding command
poetry run carchive embed all --min-word-count 7
