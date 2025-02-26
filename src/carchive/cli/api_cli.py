"""
CLI commands for running the API server.
"""

import typer
import sys
import os
from pathlib import Path
from flask import Flask
import logging

app = typer.Typer(name="api", help="Commands for managing the API server")

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="The host to bind to"),
    port: int = typer.Option(5000, "--port", "-p", help="The port to bind to"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode")
):
    """
    Run the API server.
    """
    # Enable debug mode if requested
    if debug:
        os.environ['FLASK_ENV'] = 'development'
    
    # Create Flask app
    from carchive.api import create_app
    flask_app = create_app()
    
    # Run the app
    typer.echo(f"Starting API server at http://{host}:{port}")
    flask_app.run(host=host, port=port, debug=debug)

@app.command()
def info():
    """
    Show information about the API.
    """
    typer.echo("carchive API Information")
    typer.echo("------------------------")
    typer.echo("The API provides access to conversations, messages, and media in the carchive2 database.")
    typer.echo("")
    typer.echo("Available Endpoints:")
    typer.echo("  /api/health        - Health check endpoint")
    typer.echo("  /api/conversations - Access to conversations")
    typer.echo("  /api/messages      - Access to messages")
    typer.echo("  /api/media         - Access to media files")
    typer.echo("  /api/search        - Search functionality")
    typer.echo("")
    typer.echo("To start the API server, use:")
    typer.echo("  carchive api serve")