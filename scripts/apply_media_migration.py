#!/usr/bin/env python3
# scripts/apply_media_migration.py

"""
Apply database schema changes for enhanced media handling.
This script directly executes SQL to add the new media fields.
"""

import os
import sys
import argparse

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from carchive.database.session import get_session
from sqlalchemy import text

def apply_migration(sql_file_path, dry_run=False):
    """Execute the SQL file to apply the migration."""
    with open(sql_file_path, 'r') as f:
        sql = f.read()
    
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    
    if dry_run:
        print("DRY RUN: The following SQL would be executed:")
        for stmt in statements:
            print(f"---\n{stmt}\n---")
        return
    
    with get_session() as session:
        try:
            for stmt in statements:
                if stmt:
                    print(f"Executing: {stmt[:80]}{'...' if len(stmt) > 80 else ''}")
                    session.execute(text(stmt))
            session.commit()
            print("Migration applied successfully!")
        except Exception as e:
            session.rollback()
            print(f"Error applying migration: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Apply media table schema migration")
    parser.add_argument('--sql-file', default='scripts/add_media_enhanced_fields.sql', 
                        help='Path to the SQL file with migration statements')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show SQL that would be executed without actually running it')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.sql_file):
        print(f"Error: SQL file not found at {args.sql_file}")
        return 1
    
    apply_migration(args.sql_file, args.dry_run)
    return 0

if __name__ == "__main__":
    sys.exit(main())