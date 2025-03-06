#!/bin/bash
# Database maintenance script using the new consolidated CLI commands
# This script replaces the various apply_*_fix.sh scripts

# Show database info
echo "=== Database Information ==="
poetry run carchive db info

# Validate database schema
echo ""
echo "=== Validating Database Schema ==="
poetry run carchive db validate

# Ask if user wants to fix issues
echo ""
read -p "Apply all database fixes? (y/n): " apply_fixes

if [[ "$apply_fixes" =~ ^[Yy]$ ]]; then
    echo ""
    echo "=== Applying Database Fixes ==="
    poetry run carchive db fix all
    
    echo ""
    echo "=== Re-validating Database Schema ==="
    poetry run carchive db validate
    
    # Ask if user wants to run embeddings
    echo ""
    read -p "Run embedding process? (y/n): " run_embedding
    
    if [[ "$run_embedding" =~ ^[Yy]$ ]]; then
        echo ""
        echo "=== Running Embedding Process ==="
        poetry run carchive embed all --min-word-count 7
    fi
fi

echo ""
echo "Database maintenance complete!"