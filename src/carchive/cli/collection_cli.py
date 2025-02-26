# src/carchive/cli/collection_cli.py
"""
CLI commands to manage collections (anchored searches, listing, exporting).
"""
import typer
from carchive.collections.collection_manager import CollectionManager
from carchive.collections.schemas import CollectionCreateSchema
from carchive.collections.render_engine import render_collection_to_html
from carchive.database.session import get_session
from pathlib import Path

collection_app = typer.Typer(help="Commands to manage or create collections.")


@collection_app.command("create")
def create_collection_cmd(name: str):
    """
    Creates a new empty collection with the given name.
    """
    coll_data = CollectionCreateSchema(name=name)
    coll = CollectionManager.create_collection(coll_data)
    typer.echo(f"Created collection {coll.id}: {coll.name}")

@collection_app.command("list")
def list_collections_cmd():
    """
    List existing collections.
    """
    from carchive.database.models import Collection
    with get_session() as session:
        cols = session.query(Collection).all()
        typer.echo(f"Found {len(cols)} collections")
        for c in cols:
            typer.echo(f"- {c.id}: {c.name}")

@collection_app.command("create-from-search")
def create_from_search_command(
    name: str = typer.Option(..., "--name", help="Name for the new collection"),
    criteria_file: str = typer.Option(..., "--criteria", help="Path to the search criteria JSON file"),
    search_type: str = typer.Option("message", "--type", help="Search type: message or conversation"),
    embed: bool = typer.Option(False, "--embed", help="Generate embeddings for results")
):
    from carchive.search.search_manager import SearchManager

    manager = SearchManager()
    try:
        collection = manager.search_and_create_collection(
            criteria_file=criteria_file,
            collection_name=name,
            search_type=search_type,
            embed=embed
        )
        typer.echo(f"Created collection {collection.id}: {collection.name}")
    except Exception as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(1)

@collection_app.command("render")
def render_collection_cmd(collection_name: str,
                          output_file: Path = Path("collection_render.html"),
                          include_convo: bool = False,
                          include_metadata: bool = False):
    """
    Render a collection with optional conversation info and metadata.
    """
    try:
        render_collection_to_html(
            collection_name,
            output_file,
            include_conversation_info=include_convo,
            include_message_metadata=include_metadata
        )
        typer.echo(f"Collection '{collection_name}' rendered to {output_file}")
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)

@collection_app.command("render-conversation")
def render_conversation_cmd(conversation_id: str, output_file: Path = Path("conversation_render.html")):
    """
    Render a full conversation as an HTML page with improved styling and MathJax support.
    """
    from carchive.collections.render_engine import render_conversation_to_html
    try:
        render_conversation_to_html(conversation_id, output_file)
        typer.echo(f"Conversation '{conversation_id}' rendered to {output_file}")
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)

@collection_app.command("embed-collection")
def embed_collection_cmd(
    name: str = typer.Option(..., "--name", help="Name of the collection"),
    provider: str = typer.Option("openai", help="Embedding provider"),
    model_version: str = typer.Option("text-embedding-ada-002", help="Model version to use"),
    store_in_db: bool = typer.Option(True, help="Whether to store embeddings in the database")
):
    """
    Generate embeddings for all messages in the specified collection.
    """
    from carchive.database.models import Collection, Message
    from carchive.embeddings.schemas import EmbeddingRequestSchema, EmbeddingTargetSchema
    from carchive.embeddings.embed_manager import EmbeddingManager

    manager = EmbeddingManager()  # Instantiate the embedding manager
    messages_to_embed = []

    with get_session() as session:
        # Retrieve the collection by name
        collection = session.query(Collection).filter_by(name=name).first()
        if not collection:
            typer.echo(f"Collection '{name}' not found.")
            raise typer.Exit(1)

        # Gather all message texts from the collection
        for item in collection.items:
            if item.message_id:
                msg = session.query(Message).filter_by(id=item.message_id).first()
                if msg and msg.content:
                    messages_to_embed.append(msg.content)

    if not messages_to_embed:
        typer.echo(f"No messages found in collection '{name}' for embedding.")
        raise typer.Exit(1)

    # Prepare embedding targets
    targets = [EmbeddingTargetSchema(text=text) for text in messages_to_embed]

    embedding_request = EmbeddingRequestSchema(
        provider=provider,
        model_version=model_version,
        store_in_db=store_in_db,
        targets=targets
    )

    # Generate embeddings using EmbeddingManager
    results = manager.embed_texts(embedding_request)

    typer.echo(f"Generated embeddings for {len(results)} messages in collection '{name}'.")
