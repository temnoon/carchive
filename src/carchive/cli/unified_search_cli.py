"""
CLI interface for the unified search system.

This module provides a command-line interface for the unified search system,
allowing users to search across all entity types with consistent behavior.
"""

import typer
import logging
from typing import List, Optional
from datetime import datetime
from enum import Enum
import json

from carchive.search.unified import (
    SearchManager, SearchCriteria, SearchMode, EntityType, SortOrder, DateRange
)

# Set up logging
logger = logging.getLogger(__name__)

# Create Typer application
search_app = typer.Typer(help="Unified search across all content types.")


class OutputFormat(str, Enum):
    """Output formats for search results."""
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


@search_app.command("all")
def unified_search(
    # Text search parameters
    query: Optional[str] = typer.Argument(
        None, help="Text to search for"
    ),
    mode: SearchMode = typer.Option(
        SearchMode.SUBSTRING, "--mode", "-m",
        help="Search mode: substring, exact, any_word, all_words, regex"
    ),
    
    # Entity type parameters
    entity_types: Optional[List[str]] = typer.Option(
        None, "--entity", "-e", 
        help="Entity types to search: message, conversation, chunk, gencom, media, all"
    ),
    gencom_types: Optional[List[str]] = typer.Option(
        None, "--gencom-type", "-g",
        help="Specific gencom types to search (e.g., category, summary)"
    ),
    
    # Role and provider filters
    roles: Optional[List[str]] = typer.Option(
        None, "--role", "-r",
        help="Filter by roles (e.g., user, assistant)"
    ),
    providers: Optional[List[str]] = typer.Option(
        None, "--provider", "-p",
        help="Filter by providers (e.g., claude, chatgpt)"
    ),
    
    # Date filtering
    days: Optional[int] = typer.Option(
        None, "--days", "-d",
        help="Only include results from the last N days"
    ),
    start_date: Optional[datetime] = typer.Option(
        None, "--start-date",
        help="Start date for filtering (format: YYYY-MM-DD)"
    ),
    end_date: Optional[datetime] = typer.Option(
        None, "--end-date",
        help="End date for filtering (format: YYYY-MM-DD)"
    ),
    
    # Pagination and sorting
    limit: int = typer.Option(
        10, "--limit", "-l",
        help="Maximum number of results to return"
    ),
    offset: int = typer.Option(
        0, "--offset", "-o",
        help="Number of results to skip (for pagination)"
    ),
    sort_by: SortOrder = typer.Option(
        SortOrder.DATE_DESC, "--sort", "-s",
        help="Sort order: relevance, date_desc, date_asc, alpha_asc, alpha_desc"
    ),
    
    # Advanced filters
    conversation_id: Optional[str] = typer.Option(
        None, "--conversation-id", "-c",
        help="Filter by conversation ID"
    ),
    
    # Output formatting
    format: OutputFormat = typer.Option(
        OutputFormat.TABLE, "--format", "-f",
        help="Output format: table, json, csv"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "--out",
        help="File to write results to (if not specified, print to stdout)"
    ),
    show_metadata: bool = typer.Option(
        False, "--show-metadata",
        help="Include metadata in the output"
    )
):
    """
    Search across all content types with flexible filtering.
    
    This command allows you to search messages, conversations, chunks,
    gencom outputs, and media with consistent behavior and filtering options.
    
    Examples:
    
    # Search for "philosophy" in all entity types
    carchive search all philosophy
    
    # Search for "consciousness" in messages with role "assistant"
    carchive search all consciousness --entity message --role assistant
    
    # Search for any of the words "mind", "body", "soul" in gencom categories
    carchive search all "mind body soul" --mode any_word --entity gencom --gencom-type category
    
    # Search for exact phrase "meaning of life" in conversations
    carchive search all "meaning of life" --mode exact --entity conversation
    
    # Find recent content from the last 7 days
    carchive search all --days 7
    """
    # Convert entity_types to EntityType enum values
    entity_type_enums = []
    if entity_types:
        for entity_type in entity_types:
            try:
                entity_type_enums.append(EntityType(entity_type.lower()))
            except ValueError:
                typer.echo(f"Warning: Unknown entity type '{entity_type}'. "
                           f"Valid types are: {', '.join(e.value for e in EntityType)}")
    
    # Create date range if dates are specified
    date_range = None
    if start_date or end_date:
        date_range = DateRange(
            start=start_date,
            end=end_date
        )
    
    # Create search criteria
    criteria = SearchCriteria(
        text_query=query,
        search_mode=mode,
        entity_types=entity_type_enums or [EntityType.ALL],
        gencom_types=gencom_types,
        roles=roles,
        providers=providers,
        date_range=date_range,
        days=days,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        conversation_id=conversation_id
    )
    
    # Execute search
    search_manager = SearchManager()
    try:
        results = search_manager.search(criteria)
    except Exception as e:
        typer.echo(f"Error executing search: {e}")
        raise typer.Exit(code=1)
    
    # Format and output results
    if format == OutputFormat.TABLE:
        output = _format_results_as_table(results, show_metadata)
    elif format == OutputFormat.JSON:
        output = _format_results_as_json(results)
    elif format == OutputFormat.CSV:
        output = _format_results_as_csv(results, show_metadata)
    else:
        output = _format_results_as_table(results, show_metadata)
    
    # Write to file or stdout
    if output_file:
        try:
            with open(output_file, 'w') as f:
                f.write(output)
            typer.echo(f"Results saved to {output_file}")
        except Exception as e:
            typer.echo(f"Error writing to output file: {e}")
            typer.echo(output)
    else:
        typer.echo(output)


def _format_results_as_table(results, show_metadata=False) -> str:
    """Format search results as a text table."""
    if not results.results:
        return "No results found."
    
    # Calculate column widths
    id_width = max(len("ID"), max(len(str(r.id)[:10]) for r in results.results))
    type_width = max(len("Type"), max(len(r.entity_type) for r in results.results))
    content_width = 60  # Fixed width for content
    date_width = 19  # Fixed width for dates
    
    # Prepare header
    header = (
        f"{'ID':<{id_width}} | "
        f"{'Type':<{type_width}} | "
        f"{'Content':<{content_width}} | "
        f"{'Created':<{date_width}}"
    )
    if show_metadata:
        header += " | Metadata"
    
    # Prepare separator
    separator = "-" * len(header)
    
    # Prepare rows
    rows = [header, separator]
    for result in results.results:
        content = result.content or ""
        if len(content) > content_width:
            content = content[:content_width-3] + "..."
        
        row = (
            f"{str(result.id)[:10]:<{id_width}} | "
            f"{result.entity_type:<{type_width}} | "
            f"{content:<{content_width}} | "
            f"{result.created_at.strftime('%Y-%m-%d %H:%M:%S'):<{date_width}}"
        )
        
        if show_metadata:
            metadata_str = " | "
            if result.role:
                metadata_str += f"Role: {result.role}, "
            if result.conversation_id:
                metadata_str += f"Conv: {result.conversation_id[:8]}, "
            metadata_str += ", ".join(f"{k}: {v}" for k, v in result.metadata.items() 
                                      if k not in ["role", "conversation_id"])
            row += metadata_str
        
        rows.append(row)
    
    # Add summary
    rows.append(separator)
    rows.append(f"Found {results.total_count} results (showing {len(results.results)})")
    rows.append(f"Query time: {results.query_time_ms:.2f}ms")
    
    return "\n".join(rows)


def _format_results_as_json(results) -> str:
    """Format search results as JSON."""
    # Convert to dict for JSON serialization
    results_dict = {
        "results": [result.dict() for result in results.results],
        "total_count": results.total_count,
        "query_time_ms": results.query_time_ms,
        "criteria": results.criteria.dict()
    }
    
    # Handle datetime serialization
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
    
    return json.dumps(results_dict, indent=2, cls=DateTimeEncoder)


def _format_results_as_csv(results, show_metadata=False) -> str:
    """Format search results as CSV."""
    if not results.results:
        return "No results found."
    
    # Prepare header
    header = "id,entity_type,content,created_at"
    if show_metadata:
        header += ",role,conversation_id,metadata"
    
    # Prepare rows
    rows = [header]
    for result in results.results:
        content = result.content or ""
        # Escape CSV special characters
        content = f'"{content.replace(\'"\', \'""\')}".strip()[:1000]'
        
        row = f"{result.id},{result.entity_type},{content},{result.created_at.isoformat()}"
        
        if show_metadata:
            role = result.role or ""
            conversation_id = result.conversation_id or ""
            metadata = str(result.metadata).replace(",", ";")
            row += f",{role},{conversation_id},{metadata}"
        
        rows.append(row)
    
    return "\n".join(rows)


if __name__ == "__main__":
    search_app()