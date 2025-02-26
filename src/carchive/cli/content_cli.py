# carchive2/cli/content_cli.py
import typer
from carchive.pipelines.content_tasks import ContentTaskManager

app = typer.Typer()

@app.command("process")
def process_task(message_id: str, task: str):
    manager = ContentTaskManager(provider="openai")
    result = manager.run_task_for_message(message_id=message_id, task=task)
    typer.echo(f"Task '{task}' processed for message {message_id}. Output stored with ID {result.id}")

if __name__ == "__main__":
    app()
