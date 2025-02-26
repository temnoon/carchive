# src/carchive/cli/search_cli.py
import typer
import json
import re
from datetime import datetime
from typing import Optional
from carchive.search.search import search_messages, search_conversations, search_messages_with_conversation
from carchive.schemas.db_objects import ConversationRead, MessageRead
from carchive.schemas.search import SearchCriteria
from pydantic import ValidationError


search_app = typer.Typer(help="Commands to search conversations/messages/chunks.")

@search_app.command("messages")
def message_search_cmd(query: str, limit: int = 10):
    """
    Search messages containing the given text.
    """
    results: list[MessageRead] = search_messages(query, limit)
    typer.echo(f"Found {len(results)} messages containing '{query}'")
    for msg in results:
        typer.echo(f"- Message ID: {msg.id} | Conversation ID: {msg.conversation_id}")

@search_app.command("detailed")
def detailed_search_cmd(query: str, limit: int = 10):
    """
    Search messages containing the given text along with conversation details.
    """
    results = search_messages_with_conversation(query, limit)
    if not results:
        typer.echo("No results found.")
        return

    for row in results:
        typer.echo(f"Message ID: {row.message_id}")
        typer.echo(f"Conversation ID: {row.conversation_id}")
        typer.echo(f"Title: {row.conversation_title} | Created At: {row.conversation_created_at}")
        typer.echo(f"Content: {row.content}")
        typer.echo("-" * 40)

@search_app.command("advanced")
def advanced_search_cmd(criteria_file: str, output: str = "text"):
    """
    Run an advanced search based on criteria file and output results.
    """
    from carchive.search.search_schemas import AdvancedSearchCriteria
    from carchive.search.search_manager import SearchManager

    with open(criteria_file) as f:
        criteria_data = json.load(f)
    criteria = AdvancedSearchCriteria(**criteria_data)

    results = SearchManager.advanced_search(criteria)

    if output == "json":
        typer.echo(json.dumps([obj.dict() for obj in results], indent=2))
    else:
        for obj in results:
            typer.echo(f"{obj}")

@search_app.command("save-criteria")
def save_criteria_cmd(
    output_file: Optional[str] = None
):
    """
    Interactively create search criteria and save to a JSON file.
    """
    # Prompt user for criteria
    text_query = typer.prompt("Enter text query (leave blank if none)", default="")
    meta_filters_input = typer.prompt(
        "Enter metadata filters as JSON (e.g., {\"source\": \"chatgpt\"}) or leave blank",
        default=""
    )
    top_k_input = typer.prompt("Enter top_k value", default="10")

    # Parse meta_filters JSON if provided
    meta_filters = None
    if meta_filters_input.strip():
        try:
            meta_filters = json.loads(meta_filters_input)
        except json.JSONDecodeError:
            typer.echo("Invalid JSON for metadata filters. Using None.")
            meta_filters = None

    # Build criteria dictionary
    criteria_data = {
        "text_query": text_query or None,
        "meta_filters": meta_filters,
        "top_k": int(top_k_input)
    }

    # Validate criteria using Pydantic
    try:
        criteria_model = SearchCriteria(**criteria_data)
    except ValidationError as e:
        typer.echo(f"Validation error: {e}")
        raise typer.Exit(code=1)

    # Auto-generate filename if not provided
    if not output_file:
        # Create a slug from the text query
        slug = re.sub(r'\W+', '_', text_query)[:50] or "criteria"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"criteria_{slug}_{timestamp}.json"

    # Save the validated criteria to a file
    with open(output_file, "w") as f:
        json.dump(criteria_model.dict(), f, indent=2)

    typer.echo(f"Search criteria saved to {output_file}")

@search_app.command("apply")
def apply_search(
    criteria: str = typer.Option(..., help="Path to criteria JSON file"),
    type: str = typer.Option(..., help="Type of search: conversation or message")
):
    """
    Apply saved search criteria from a file and perform the search.
    """
    try:
        with open(criteria, "r") as f:
            criteria_data = json.load(f)
    except Exception as e:
        typer.echo(f"Error reading criteria file: {e}")
        raise typer.Exit(1)

    text_query = criteria_data.get("text_query")
    top_k = criteria_data.get("top_k", 10)

    if not text_query:
        typer.echo("No text query found in criteria file.")
        raise typer.Exit(1)

    if type.lower() == "conversation":
        results: list[ConversationRead] = search_conversations(text_query, limit=top_k)
        typer.echo(f"Found {len(results)} conversations matching '{text_query}':")
        for convo in results:
            typer.echo(f"- {convo.id} | {convo.title}")
    elif type.lower() == "message":
        results: list[MessageRead] = search_messages(text_query, limit=top_k)
        typer.echo(f"Found {len(results)} messages containing '{text_query}':")
        for msg in results:
            typer.echo(f"- {msg.id} | Conversation ID: {msg.conversation_id}")
    else:
        typer.echo("Unsupported type specified. Use 'conversation' or 'message'.")
        raise typer.Exit(1)
