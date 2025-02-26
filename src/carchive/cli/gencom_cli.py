# carchive2/src/carchive2/cli/gencom_cli.py
import typer
import logging
from typing import Optional
from sqlalchemy import func, String, cast
from sqlalchemy.dialects.postgresql import JSONB
from carchive.database.session import get_session
from carchive.database.models import Message
from carchive.pipelines.content_tasks import ContentTaskManager

gencom_app = typer.Typer(help="Commands for generating agent comments on content.")
logger = logging.getLogger(__name__)

@gencom_app.command("all")
def gencom_all(
    min_word_count: int = typer.Option(
        5, "--min-word-count", help="Minimum words a message must have."
    ),
    role: str = typer.Option(
        "user", "--role", help="Only process messages with meta_info['author_role'] equal to this value."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Optional limit on the number of messages to process."
    ),
    prompt_template: Optional[str] = typer.Option(
        None, "--prompt-template", help="Prompt template (use {content} as placeholder)."
    ),
    interactive: bool = typer.Option(
        False, "--interactive", help="If set and no prompt template is provided, prompt for one interactively."
    ),
    override: bool = typer.Option(
        False, "--override", help="Force reprocessing even if an output already exists."
    ),
    provider: str = typer.Option(
        "ollama", "--provider", help="Content agent provider to use (e.g., 'ollama', 'openai')."
    )
):
    """
    Generate an AI comment on each message that meets the criteria.

    The generated comment is stored as an AgentOutput with output_type 'gencom'.
    By default, only messages with meta_info['author_role'] equal to 'user'
    and with at least the specified word count are processed.

    If --interactive is set and no prompt template is provided, you will be prompted to enter one.
    """
    if not prompt_template and interactive:
        prompt_template = typer.prompt("Enter the prompt template (use {content} as placeholder)")
    elif not prompt_template:
        prompt_template = "Please provide a comment on the following content:\n\n{content}"

    logger.info("Starting generated comment process for messages with role '%s'.", role)
    manager = ContentTaskManager(provider=provider)

    with get_session() as session:
        # Build base query: messages with non-null content and at least the min word count
        word_count_expr = func.array_length(func.regexp_split_to_array(Message.content, r'\s+'), 1)
        base_query = session.query(Message).filter(Message.content.isnot(None))
        base_query = base_query.filter(word_count_expr >= min_word_count)
        total_without_role = base_query.count()
        logger.info("Found %d messages meeting word count criteria.", total_without_role)

        # Filter by role: cast meta_info to JSONB and extract the key 'author_role'
        query = base_query.filter(
            func.lower(
                func.coalesce(
                    func.jsonb_extract_path_text(cast(Message.meta_info, JSONB), "author_role"),
                    ''
                )
            ) == role.lower()
        )
        if limit:
            query = query.limit(limit)
        messages = query.all()

    total = len(messages)
    logger.info("After filtering by role '%s', found %d messages.", role, total)

    processed = 0
    failed = 0
    for msg in messages:
        try:
            output = manager.run_task_for_message(
                message_id=str(msg.id),
                task="gencom",
                prompt_template=prompt_template,
                override=override
            )
            logger.info("Message %s processed (AgentOutput ID: %s).", msg.id, output.id)
            processed += 1
        except Exception as e:
            logger.error("Error processing message %s: %s", msg.id, e)
            failed += 1

    typer.echo(f"Generated comments complete. Processed: {processed}, Failed: {failed}.")

if __name__ == "__main__":
    gencom_app()
