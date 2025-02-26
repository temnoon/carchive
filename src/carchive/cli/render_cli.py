# src/carchive/cli/render_cli.py
# carchive2/cli/render_cli.py
import typer
from carchive.rendering.conversation_renderer import render_conversation_html

render_app = typer.Typer(help="Render HTML views.")

@render_app.command("conversation")
def conversation_cmd(conversation_id: str, output_file: str = "conversation.html"):
    """
    Render a conversation to an HTML file.
    """
    render_conversation_html(conversation_id, output_file)
    typer.echo(f"Conversation {conversation_id} rendered to {output_file}")
