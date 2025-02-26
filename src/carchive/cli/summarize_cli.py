# carchive2/src/carchive2/cli/summarize_cli.py
import typer
import logging
from typing import Optional
from sqlalchemy import func
from carchive.database.session import get_session
from carchive.database.models import Message
from carchive.pipelines.content_tasks import ContentTaskManager

summarize_app = typer.Typer(help="Commands for generating summaries using content agents.")
logger = logging.getLogger(__name__)

@summarize_app.command("summarize-user")
def summarize_user(
    min_word_count: int = typer.Option(
        5,
        "--min-word-count",
        help="Minimum number of words a message must have to qualify for summarization."
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Optional limit on the number of messages to process."
    ),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        help="Content agent provider to use for summarization (e.g., 'openai', 'ollama')."
    ),
    override: bool = typer.Option(
        False,
        "--override",
        help="If set, force reprocessing even if a summary already exists."
    ),
    role: str = typer.Option(
        "user",
        "--role",
        help="Only process messages with meta_info['author_role'] equal to this value (default: 'user')."
    )
):
    """
    Generate summaries for all messages in the database that have at least `min_word_count` words
    and where the message's meta_info indicates the specified role (default is 'user').
    Each summary is stored as an AgentOutput linked to its source message.
    """
    logger.info("Starting summarization for messages with role '%s'.", role)

    # Instantiate our dedicated content task manager.
    manager = ContentTaskManager(provider=provider)

    with get_session() as session:
        # Build an expression to count words in the message content.
        word_count_expr = func.array_length(func.regexp_split_to_array(Message.content, r'\s+'), 1)
        query = session.query(Message).filter(Message.content.isnot(None))
        query = query.filter(word_count_expr >= min_word_count)
        # Add a filter on the JSON meta_info to select only messages with the desired role.
        query = query.filter(Message.meta_info["author_role"].astext == role)
        if limit:
            query = query.limit(limit)
        messages = query.all()

    total = len(messages)
    logger.info("Found %d messages with at least %d words and role '%s'.", total, min_word_count, role)

    processed = 0
    failed = 0

    # Process each message: run summarization and store the result.
    for msg in messages:
        try:
            output = manager.run_task_for_message(message_id=str(msg.id), task="summary", override=override)
            logger.info("Message %s summarized successfully (AgentOutput ID: %s).", msg.id, output.id)
            processed += 1
        except Exception as e:
            logger.error("Error summarizing message %s: %s", msg.id, e)
            failed += 1

    typer.echo(f"Summarization complete. Processed: {processed} messages, Failed: {failed}.")
