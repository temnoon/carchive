# carchive2/src/carchive2/cli/embed_cli.py

"""
CLI commands for manually embedding text or entire messages.
"""

import typer
from typing import List, Optional
from carchive.embeddings.embed_manager import EmbeddingManager
from carchive.embeddings.schemas import (
    EmbeddingRequestSchema,
    EmbeddingTargetSchema,
    EmbeddingResultSchema,
    EmbedAllOptions
)
from carchive.database.session import get_session
from carchive.database.models import Collection, Message
from carchive.core.config import EMBEDDING_PROVIDER, EMBEDDING_MODEL_NAME
from pydantic import ValidationError
import logging

embed_app = typer.Typer(help="Commands for generating and storing embeddings.")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

@embed_app.command("text")
def embed_text_cmd(
    text: str,
    provider: str = typer.Option(
        EMBEDDING_PROVIDER,
        "--provider",
        help="Embedding provider to use (e.g., 'openai', 'ollama').",
        show_default=True
    ),
    model_version: str = typer.Option(
        EMBEDDING_MODEL_NAME,
        "--model-version",
        help="Specific model version to use for embeddings.",
        show_default=True
    )
):
    """
    Generate and store an embedding for a given text string, using a specified provider and model.
    """
    emb_obj = embed_text(text, provider, model_version)
    if emb_obj:
        typer.echo(f"Created embedding: {emb_obj.db_id}")
    else:
        typer.echo("Failed to generate embedding.")

@embed_app.command("collection")
def embed_collection_cmd(
    collection_name: str = typer.Argument(..., help="Name of the collection"),
    provider: str = typer.Option(
        EMBEDDING_PROVIDER,
        "--provider",
        help="Embedding provider to use (e.g., 'openai', 'ollama').",
        show_default=True
    ),
    model_version: str = typer.Option(
        EMBEDDING_MODEL_NAME,
        "--model-version",
        help="Specific model version to use for embeddings.",
        show_default=True
    )
):
    """
    Generate embeddings for all messages in the specified collection.
    """
    manager = EmbeddingManager()
    results = manager.embed_collection(
        collection_name=collection_name,
        provider=provider,
        model_version=model_version
    )
    typer.echo(f"Generated embeddings for {len(results)} messages in collection '{collection_name}'.")

@embed_app.command("all")
def embed_all_cmd(
    min_word_count: int = typer.Option(
        5,
        "--min-word-count",
        help="Minimum number of words required to embed a message.",
        show_default=True
    ),
    include_roles: Optional[List[str]] = typer.Option(
        None,
        "--include-roles",
        help="List of roles to include (e.g., 'user', 'assistant'). If not set, includes all roles.",
        metavar="ROLE",
        show_default=False
    ),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Embedding provider to use (e.g., 'openai', 'ollama').",
        show_default=True
    ),
    model_version: str = typer.Option(
        "nomic-embed-text",
        "--model-version",
        help="Specific model version to use for embeddings.",
        show_default=True
    ),
    store_in_db: bool = typer.Option(
        True,
        "--store-in-db/--no-store-in-db",
        help="Whether to store embeddings in the database.",
        show_default=True
    )
):
    """
    Embed all messages with more than a specified number of words.
    Excludes messages with empty or non-substantive content.
    """
    # Create EmbedAllOptions instance
    try:
        options = EmbedAllOptions(
            min_word_count=min_word_count,
            include_roles=include_roles,
            exclude_empty=True
        )
    except ValidationError as e:
        typer.echo(f"Invalid options: {e}")
        raise typer.Exit(code=1)

    # Initialize the EmbeddingManager
    manager = EmbeddingManager()

    # Perform embedding
    try:
        count = manager.embed_all_messages(
            options=options,
            provider=provider,
            model_version=model_version,
            store_in_db=store_in_db
        )
        typer.echo(f"Successfully embedded {count} messages.")
    except Exception as e:
        logger.error(f"Error during embedding: {e}")
        typer.echo(f"An error occurred: {e}")
        raise typer.Exit(code=1)

def embed_text(text: str, provider: str, model_version: str):
    """
    Helper function to embed a single text.
    """
    manager = EmbeddingManager()
    request = EmbeddingRequestSchema(
        provider=provider,
        model_version=model_version,
        store_in_db=True,
        targets=[EmbeddingTargetSchema(text=text)]
    )
    try:
        results = manager.embed_texts(request)
        if results:
            return results[0]
        else:
            return None
    except Exception as e:
        logger.error(f"Failed to embed text: {e}")
        return None

@embed_app.command("summarize")
def summarize_cmd(
    provider: str = typer.Option(
        "llama3.2",
        "--provider",
        help="Summarization provider to use (default: 'llama3.2').",
        show_default=True
    ),
    model_name: str = typer.Option(
        "llama3.2",
        "--model-name",
        help="Specific model name to use for summarization.",
        show_default=True
    )
):
    """
    Generate summaries for all messages that have embeddings.
    """
    # Initialize the EmbeddingManager
    manager = EmbeddingManager()

    # Perform summarization
    try:
        count = manager.summarize_messages(
            provider=provider,
            model_name=model_name
        )
        typer.echo(f"Successfully summarized {count} messages.")
    except Exception as e:
        logger.error(f"Error during summarization: {e}")
        typer.echo(f"An error occurred: {e}")
        raise typer.Exit(code=1)
