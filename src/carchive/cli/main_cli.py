"""
Top-level CLI that aggregates sub-apps from ingestion_cli, search_cli, etc.
"""

import logging
import typer
from carchive.cli.summarize_cli import summarize_app
from carchive.cli.ingestion_cli import ingest_app
from carchive.cli.search_cli import search_app
from carchive.cli.embed_cli import embed_app
from carchive.cli.collection_cli import collection_app
from carchive.cli.gencom_cli import gencom_app
from carchive.cli.media_cli import app as media_app
from carchive.cli.api_cli import app as api_app  # Import the API CLI


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s - %(message)s"
)

main_app = typer.Typer(help="carchive CLI")

# Add subcommands as Typer sub-apps:
main_app.add_typer(ingest_app, name="ingest")
main_app.add_typer(search_app, name="search")
main_app.add_typer(embed_app, name="embed")
main_app.add_typer(collection_app, name="collection")
main_app.add_typer(summarize_app, name="summarize")
main_app.add_typer(gencom_app, name="gencom")
main_app.add_typer(media_app, name="media")
main_app.add_typer(api_app, name="api")  # Add the API CLI


def main():
    main_app()

if __name__ == "__main__":
    main()
