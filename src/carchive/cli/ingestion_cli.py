"""
CLI commands related to file ingestion.

Focuses on CLI argument parsing & calling ingestion logic from ingestion/ingest.py.
"""

import typer
from pathlib import Path

# We'll import the actual ingestion logic from the ingestion folder:
from carchive.ingestion.ingest import ingest_file

ingest_app = typer.Typer(help="Commands to ingest chat data into the database.")

@ingest_app.command("file")
def ingest_file_cmd(filepath: str):
    """
    Ingest a JSON or ZIP file containing conversation data.
    """
    path = Path(filepath)
    if not path.exists():
        typer.echo(f"File not found: {filepath}")
        raise typer.Exit(code=1)

    typer.echo(f"Starting ingestion of file: {filepath}")
    ingest_file(path)
    typer.echo("Ingestion complete.")
