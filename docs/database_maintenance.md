# Database Maintenance Guide

This guide covers the database maintenance features in carchive, including common issues, fixes, and validation procedures.

## Overview

The carchive system uses a PostgreSQL database with pgvector extension for vector storage and search. Database maintenance includes:

1. Fixing vector dimensions in the embeddings table
2. Managing parent-child relationships
3. Adjusting table constraints
4. Adding necessary indexes

All these operations are now centralized in the `carchive db` command.

## Common Database Operations

### Viewing Database Information

```bash
# Check basic database information
poetry run carchive db info
```

This displays database version and table counts.

### Validating Database Schema

```bash
# Validate the database schema and identify issues
poetry run carchive db validate
```

This command checks for common schema issues and suggests fixes if problems are found.

### Applying Database Fixes

```bash
# Fix vector dimension issues
poetry run carchive db fix vector-dimension

# Fix parent type constraint
poetry run carchive db fix parent-type

# Make parent columns nullable
poetry run carchive db fix embeddings-nullable

# Add parent relationship columns
poetry run carchive db fix parent-columns

# Apply all fixes in the correct order
poetry run carchive db fix all

# Preview changes without applying them
poetry run carchive db fix all --dry-run
```

## Common Issues and Solutions

### Vector Dimension Issues

**Problem**: Vector dimension mismatch (e.g., trying to insert a 768-dimension vector when the table expects 1536)

**Solution**:
```
poetry run carchive db fix vector-dimension
```

This fix:
1. Drops the existing vector index
2. Updates the vector dimension to 768
3. Recreates the vector index

### Parent Type Constraint Issues

**Problem**: Cannot insert embeddings with certain parent_type values

**Solution**:
```
poetry run carchive db fix parent-type
```

This fix updates the constraint to allow all valid parent types, including 'raw_text'.

### Parent Reference Issues

**Problem**: Missing parent columns for direct references

**Solution**:
```
poetry run carchive db fix parent-columns
```

This adds dedicated columns for parent references (parent_message_id, parent_chunk_id) with proper foreign key constraints.

## Legacy Scripts

The following legacy shell scripts have been replaced by the `carchive db` command:

- `apply_vector_fix.sh` → `carchive db fix vector-dimension`
- `apply_constraint_fix.sh` → `carchive db fix parent-type`
- `apply_embeddings_fix.sh` → `carchive db fix embeddings-nullable`
- `apply_embedding_columns.sh` → `carchive db fix parent-columns`
- `run_embedding_with_fixes.sh` → `carchive db fix all && carchive embed all`

## Advanced Operations

### Custom SQL Execution

For advanced database operations not covered by the built-in commands, you can still use the PostgreSQL client directly:

```bash
psql -U carchive_app -d carchive04_db
```

### Database Backups

It's recommended to back up your database before significant operations:

```bash
pg_dump -U carchive_app carchive04_db > carchive_backup_$(date +%Y%m%d).sql
```

## Troubleshooting

If database fixes fail, check:

1. PostgreSQL service is running
2. Database connection settings are correct
3. pgvector extension is installed
4. Your user has sufficient permissions

Run validation to identify specific issues:

```bash
poetry run carchive db validate
```

## Integration with Embedding System

After applying database fixes, you may need to update your embeddings:

```bash
# First fix database issues
poetry run carchive db fix all

# Then generate embeddings
poetry run carchive embed all --min-word-count 7
```