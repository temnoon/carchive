"""
Command-line interface for migration features.
"""
import os
import logging
import typer
from typing import Optional
from pathlib import Path

from carchive.migration.migration_service import MigrationService
from carchive.migration.claude_adapter import CLAUDE_PROVIDER_ID

app = typer.Typer(name="migration", help="Migration tools for carchive")

@app.command("chatgpt")
def migrate_chatgpt(
    archive_path: Path = typer.Argument(
        ..., help="Path to conversations.json file"
    ),
    db_name: str = typer.Option(
        "carchive04_db", help="Database name"
    ),
    db_user: str = typer.Option(
        "carchive_app", help="Database user"
    ),
    db_password: Optional[str] = typer.Option(
        None, help="Database password"
    ),
    db_host: str = typer.Option(
        "localhost", help="Database host"
    ),
    db_port: int = typer.Option(
        5432, help="Database port"
    ),
    media_dir: Optional[Path] = typer.Option(
        None, help="Directory containing media files (defaults to archive_path's directory)"
    ),
    target_media_dir: Optional[Path] = typer.Option(
        None, help="Directory to copy media files to (defaults to ../media/chatgpt)"
    ),
    dalle_dir: Optional[Path] = typer.Option(
        None, help="Directory containing DALL-E generated images (often 'dalle-generations' subfolder)"
    ),
    log_level: str = typer.Option(
        "INFO", help="Logging level"
    )
):
    """
    Migrate ChatGPT archive to carchive database.
    """
    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Validate input
    if not archive_path.exists():
        typer.echo(f"Error: Archive file {archive_path} does not exist", err=True)
        raise typer.Exit(1)
    
    # Set defaults
    if media_dir is None:
        media_dir = archive_path.parent
    
    if target_media_dir is None:
        target_media_dir = Path(str(archive_path.parent.parent)) / "media" / "chatgpt"
    
    # Create database connection string
    db_connection = f"postgresql://{db_user}"
    if db_password:
        db_connection += f":{db_password}"
    db_connection += f"@{db_host}:{db_port}/{db_name}"
    
    # Run migration
    typer.echo(f"Starting migration from {archive_path} to {db_name}")
    typer.echo(f"Media will be copied from {media_dir} to {target_media_dir}")
    if dalle_dir:
        typer.echo(f"DALL-E images will be processed from {dalle_dir}")
    
    try:
        service = MigrationService(db_connection)
        stats = service.migrate_chatgpt_archive(
            archive_path=str(archive_path),
            media_dir=str(media_dir),
            target_media_dir=str(target_media_dir),
            dalle_dir=str(dalle_dir) if dalle_dir else None
        )
        
        # Print statistics
        typer.echo("Migration completed successfully:")
        typer.echo(f"Imported {stats.get('conversations', 0)} conversations")
        typer.echo(f"Imported {stats.get('messages', 0)} messages")
        typer.echo(f"Imported {stats.get('relations', 0)} message relations")
        typer.echo(f"Imported {stats.get('media', 0)} media files")
    except Exception as e:
        typer.echo(f"Error during migration: {e}", err=True)
        raise typer.Exit(1)

@app.command("claude")
def migrate_claude(
    conversations_file: Path = typer.Argument(
        ..., help="Path to Claude conversations.json file"
    ),
    projects_file: Optional[Path] = typer.Option(
        None, help="Path to Claude projects.json file"
    ),
    users_file: Optional[Path] = typer.Option(
        None, help="Path to Claude users.json file"
    ),
    db_name: str = typer.Option(
        "carchive04_db", help="Database name"
    ),
    db_user: str = typer.Option(
        "carchive_app", help="Database user"
    ),
    db_password: Optional[str] = typer.Option(
        None, help="Database password", envvar="CARCHIVE_DB_PASSWORD"
    ),
    db_host: str = typer.Option(
        "localhost", help="Database host"
    ),
    db_port: int = typer.Option(
        5432, help="Database port"
    ),
    media_dir: Optional[str] = typer.Option(
        None, help="Directory containing media files"
    ),
    target_media_dir: Optional[str] = typer.Option(
        None, help="Directory to copy media files to"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """
    Migrate a Claude archive to the carchive database.
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    # Check if files exist
    if not os.path.exists(conversations_file):
        typer.echo(f"Conversations file not found: {conversations_file}", err=True)
        raise typer.Exit(1)
    
    if projects_file and not os.path.exists(projects_file):
        typer.echo(f"Projects file not found: {projects_file}", err=True)
        projects_file = None
        
    if users_file and not os.path.exists(users_file):
        typer.echo(f"Users file not found: {users_file}", err=True)
        users_file = None
        
    # Create connection string
    db_connection = f"postgresql://{db_user}"
    if db_password:
        db_connection += f":{db_password}"
    db_connection += f"@{db_host}:{db_port}/{db_name}"
    
    # Run migration
    typer.echo(f"Starting Claude migration from {conversations_file} to {db_name}")
    if projects_file:
        typer.echo(f"Using projects file: {projects_file}")
    if users_file:
        typer.echo(f"Using users file: {users_file}")
    if media_dir and target_media_dir:
        typer.echo(f"Media will be copied from {media_dir} to {target_media_dir}")
    
    try:
        service = MigrationService(db_connection)
        stats = service.migrate_claude_archive(
            conversations_file=str(conversations_file),
            projects_file=str(projects_file) if projects_file else None,
            users_file=str(users_file) if users_file else None,
            media_dir=media_dir,
            target_media_dir=target_media_dir
        )
        
        # Print statistics
        typer.echo("Migration completed successfully:")
        typer.echo(f"Imported {stats.get('conversations', 0)} conversations")
        typer.echo(f"Imported {stats.get('messages', 0)} messages")
        typer.echo(f"Imported {stats.get('relations', 0)} message relations")
        typer.echo(f"Imported {stats.get('media', 0)} media files")
        
    except Exception as e:
        typer.echo(f"Error during migration: {e}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app()
