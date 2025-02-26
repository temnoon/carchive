"""
Typer-based CLI commands for ingestion, search, or other tasks.
"""

import typer
from carchive.ingestion.ingest import ingest_file
from carchive.search.search import search_conversations
from carchive.cli.cluster_cli import cluster_app  # Import clustering commands
from carchive.cli.collection_cli import collection_app  # Import collection commands if not already included
from carchive.cli.embed_cli import embed_app  # Import embedding commands if not already included

app = typer.Typer()

# Add sub-commands
app.add_typer(cluster_app, name="cluster")
app.add_typer(collection_app, name="collection")
app.add_typer(embed_app, name="embed")

@app.command()
def ingest(filepath: str):
    """
    Ingest a JSON or ZIP file of chats.
    """
    typer.echo(f"Ingesting file: {filepath}")
    ingest_file(filepath)

@app.command()
def search(query: str, limit: int = 5):
    """
    Search conversation titles.
    """
    results = search_conversations(query, limit)
    typer.echo(f"Found {len(results)} conversations matching '{query}':")
    for convo in results:
        typer.echo(f"- {convo.id} | {convo.title}")

def main():
    app()

if __name__ == "__main__":
    main()
