"""
Database management CLI for carchive.

This module provides commands for database maintenance, validation, and fixes.
It replaces various shell scripts (apply_*_fix.sh) with a unified interface.
"""

import os
import logging
import subprocess
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import typer
import psycopg2
from psycopg2 import sql
from rich.console import Console
from rich.table import Table

from carchive.core.config import get_database_url
from carchive.database.engine import get_engine
from carchive.database.session import get_session

# Configure logger
logger = logging.getLogger(__name__)
console = Console()

# Create Typer app
app = typer.Typer(help="Database management commands")


class FixType(str, Enum):
    """Types of database fixes available."""
    VECTOR_DIMENSION = "vector-dimension"
    PARENT_TYPE = "parent-type"
    EMBEDDINGS_NULLABLE = "embeddings-nullable"
    PARENT_COLUMNS = "parent-columns"
    ALL = "all"


@app.command()
def info():
    """
    Display information about the database.
    """
    try:
        # Get database connection info
        db_url = get_database_url()
        
        # Connect to database
        with get_session() as session:
            # Get database version
            result = session.execute("SELECT version();")
            version = result.scalar()
            
            # Get table counts
            tables = [
                "conversations", "messages", "message_relations",
                "media", "message_media", "embeddings", "chunks"
            ]
            
            # Create a table for display
            table = Table(title="Database Information")
            table.add_column("Item", style="cyan")
            table.add_column("Value", style="green")
            
            # Add database info
            table.add_row("Database Version", version)
            
            # Add table counts
            for table_name in tables:
                result = session.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = result.scalar()
                table.add_row(f"{table_name.capitalize()} Count", str(count))
            
            console.print(table)
    
    except Exception as e:
        typer.echo(f"Error querying database: {e}")
        raise typer.Exit(code=1)


@app.command()
def fix(
    fix_type: FixType = typer.Argument(..., help="Type of fix to apply"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes")
):
    """
    Apply database fixes.
    
    This command consolidates various database fix scripts into a single interface.
    """
    fixes_to_apply = []
    
    if fix_type == FixType.ALL:
        # Apply all fixes in the correct order
        fixes_to_apply = [
            FixType.VECTOR_DIMENSION,
            FixType.EMBEDDINGS_NULLABLE,
            FixType.PARENT_TYPE,
            FixType.PARENT_COLUMNS
        ]
    else:
        fixes_to_apply = [fix_type]
    
    for fix in fixes_to_apply:
        _apply_fix(fix, dry_run)


def _apply_fix(fix_type: FixType, dry_run: bool):
    """Apply a specific database fix."""
    try:
        console.print(f"[bold blue]Applying {fix_type} fix...[/bold blue]")
        
        if fix_type == FixType.VECTOR_DIMENSION:
            _apply_vector_dimension_fix(dry_run)
        elif fix_type == FixType.PARENT_TYPE:
            _apply_parent_type_fix(dry_run)
        elif fix_type == FixType.EMBEDDINGS_NULLABLE:
            _apply_embeddings_nullable_fix(dry_run)
        elif fix_type == FixType.PARENT_COLUMNS:
            _apply_parent_columns_fix(dry_run)
        
        if not dry_run:
            console.print(f"[bold green]Successfully applied {fix_type} fix[/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Error applying {fix_type} fix: {e}[/bold red]")
        raise typer.Exit(code=1)


def _apply_vector_dimension_fix(dry_run: bool):
    """Fix vector dimension in embeddings table."""
    statements = [
        "DROP INDEX IF EXISTS vector_idx;",
        "ALTER TABLE embeddings ALTER COLUMN vector TYPE vector(768);",
        "CREATE INDEX vector_idx ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists='1000');"
    ]
    
    if dry_run:
        for stmt in statements:
            console.print(f"Would execute: {stmt}")
    else:
        with get_session() as session:
            # Check current vector type
            result = session.execute("SELECT pg_typeof(vector) FROM embeddings LIMIT 1;")
            current_type = result.scalar() if result.rowcount > 0 else "No embeddings found"
            console.print(f"Current vector type: {current_type}")
            
            # Apply the statements
            for stmt in statements:
                session.execute(stmt)
                session.commit()


def _apply_parent_type_fix(dry_run: bool):
    """Fix parent_type constraint to allow 'raw_text'."""
    statements = [
        "ALTER TABLE embeddings DROP CONSTRAINT IF EXISTS check_parent_type;",
        """
        ALTER TABLE embeddings ADD CONSTRAINT check_parent_type
        CHECK (parent_type::text = ANY (ARRAY['conversation', 'message', 'chunk', 'media', 'raw_text']::text[]));
        """
    ]
    
    if dry_run:
        for stmt in statements:
            console.print(f"Would execute: {stmt}")
    else:
        with get_session() as session:
            for stmt in statements:
                session.execute(stmt)
                session.commit()


def _apply_embeddings_nullable_fix(dry_run: bool):
    """Make parent_type and parent_id nullable in embeddings table."""
    statements = [
        "ALTER TABLE embeddings ALTER COLUMN parent_type DROP NOT NULL;",
        "ALTER TABLE embeddings ALTER COLUMN parent_id DROP NOT NULL;",
        "CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model_name, model_version);"
    ]
    
    if dry_run:
        for stmt in statements:
            console.print(f"Would execute: {stmt}")
    else:
        with get_session() as session:
            for stmt in statements:
                session.execute(stmt)
                session.commit()


def _apply_parent_columns_fix(dry_run: bool):
    """Add parent columns to embeddings table."""
    statements = [
        "ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS parent_message_id UUID REFERENCES messages(id);",
        "ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS parent_chunk_id UUID REFERENCES chunks(id);",
        "CREATE INDEX IF NOT EXISTS ix_embeddings_parent_message_id ON embeddings(parent_message_id);",
        "CREATE INDEX IF NOT EXISTS ix_embeddings_parent_chunk_id ON embeddings(parent_chunk_id);"
    ]
    
    if dry_run:
        for stmt in statements:
            console.print(f"Would execute: {stmt}")
    else:
        with get_session() as session:
            for stmt in statements:
                session.execute(stmt)
                session.commit()


@app.command()
def validate():
    """
    Validate database schema and suggest fixes if needed.
    """
    issues = []
    
    try:
        with get_session() as session:
            # Check embeddings table structure
            try:
                # Check vector dimension
                result = session.execute("SELECT pg_typeof(vector) FROM embeddings LIMIT 1;")
                if result.rowcount > 0:
                    vector_type = result.scalar()
                    if "vector(768)" not in str(vector_type):
                        issues.append(("vector-dimension", f"Vector dimension is not 768 (found {vector_type})"))
                
                # Check if parent columns exist
                result = session.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = 'embeddings' AND column_name = 'parent_message_id';
                """)
                if result.rowcount == 0:
                    issues.append(("parent-columns", "Missing parent_message_id column in embeddings table"))
                
                # Check constraints on parent_type
                result = session.execute("""
                    SELECT conname, pg_get_constraintdef(oid) 
                    FROM pg_constraint 
                    WHERE conname = 'check_parent_type';
                """)
                if result.rowcount > 0:
                    constraint_def = result.fetchone()[1]
                    if "'raw_text'" not in constraint_def:
                        issues.append(("parent-type", "parent_type constraint doesn't include 'raw_text'"))
                
                # Check nullability of parent columns
                result = session.execute("""
                    SELECT is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'embeddings' AND column_name = 'parent_type';
                """)
                if result.rowcount > 0 and result.fetchone()[0] == 'NO':
                    issues.append(("embeddings-nullable", "parent_type column is not nullable"))
                
            except Exception as e:
                issues.append(("unknown", f"Error checking embeddings table: {e}"))
    
    except Exception as e:
        typer.echo(f"Error validating database: {e}")
        raise typer.Exit(code=1)
    
    # Display results
    if issues:
        table = Table(title="Database Issues Found")
        table.add_column("Issue Type", style="cyan")
        table.add_column("Description", style="red")
        table.add_column("Fix Command", style="green")
        
        for issue_type, description in issues:
            fix_command = f"carchive db fix {issue_type}"
            table.add_row(issue_type, description, fix_command)
        
        console.print(table)
        
        # Suggest fix all command if multiple issues
        if len(issues) > 1:
            console.print("\n[bold yellow]Multiple issues found. You can fix all with:[/bold yellow]")
            console.print("[bold green]carchive db fix all[/bold green]")
    else:
        console.print("[bold green]Database schema validation passed. No issues found.[/bold green]")
