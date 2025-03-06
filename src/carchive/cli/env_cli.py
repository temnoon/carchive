"""
Environment management CLI for carchive.

This module provides commands for setting up and managing the carchive environment.
It consolidates various setup scripts into a unified interface.
"""

import os
import sys
import logging
import platform
import subprocess
import shutil
from pathlib import Path
from enum import Enum
from typing import List, Optional, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Configure logger
logger = logging.getLogger(__name__)
console = Console()

# Create Typer app
app = typer.Typer(help="Environment management commands")


class EnvType(str, Enum):
    """Types of environments that can be set up."""
    STANDARD = "standard"
    MAC_OPTIMIZED = "mac-optimized"
    MINIMAL = "minimal"


@app.command()
def info():
    """
    Display information about the current environment.
    """
    # Create a table for display
    table = Table(title="Environment Information")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    
    # Python information
    table.add_row("Python Version", platform.python_version())
    table.add_row("Python Path", sys.executable)
    
    # Platform information
    table.add_row("System", platform.system())
    table.add_row("Platform", platform.platform())
    
    # Check if running in virtual environment
    in_venv = sys.prefix != sys.base_prefix
    table.add_row("Virtual Environment", "Active" if in_venv else "Not active")
    if in_venv:
        table.add_row("Virtual Env Path", sys.prefix)
    
    # Check for Apple Silicon
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        table.add_row("Apple Silicon", "Yes")
    elif platform.system() == "Darwin":
        table.add_row("Apple Silicon", "No (Intel Mac)")
    
    # Check for key package versions
    try:
        import pkg_resources
        key_packages = [
            "typer", "flask", "sqlalchemy", "psycopg2", "pgvector", 
            "markdown", "rich", "uvicorn", "pydantic"
        ]
        
        for package in key_packages:
            try:
                version = pkg_resources.get_distribution(package).version
                table.add_row(f"{package} Version", version)
            except pkg_resources.DistributionNotFound:
                table.add_row(f"{package} Version", "Not installed")
    except ImportError:
        pass
    
    # Display database connection info if available
    try:
        from carchive.core.config import get_database_info
        db_info = get_database_info()
        if db_info:
            table.add_row("Database", f"{db_info.get('user')}@{db_info.get('host')}/{db_info.get('database')}")
    except ImportError:
        pass
    
    console.print(table)


@app.command()
def setup(
    env_type: EnvType = typer.Option(EnvType.STANDARD, help="Type of environment to set up"),
    path: str = typer.Option("./venv", help="Path for the virtual environment"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recreation of existing environment"),
    no_run_scripts: bool = typer.Option(False, "--no-run-scripts", help="Don't create run scripts"),
    no_dotenv: bool = typer.Option(False, "--no-dotenv", help="Don't create .env file if missing")
):
    """
    Set up a new environment for carchive.
    
    This replaces various setup scripts with a unified command.
    """
    if env_type == EnvType.MAC_OPTIMIZED and platform.system() != "Darwin":
        console.print("[bold red]Mac-optimized environment can only be created on macOS[/bold red]")
        raise typer.Exit(1)
    
    venv_path = Path(path).absolute()
    
    # Check if venv exists
    if venv_path.exists() and not force:
        console.print(f"[bold yellow]Environment already exists at {venv_path}[/bold yellow]")
        console.print("Use --force to recreate it")
        raise typer.Exit(1)
    
    if venv_path.exists() and force:
        console.print(f"[bold yellow]Removing existing environment at {venv_path}[/bold yellow]")
        shutil.rmtree(venv_path)
    
    # Create virtual environment
    console.print(f"[bold blue]Creating {env_type} environment at {venv_path}...[/bold blue]")
    
    try:
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to create virtual environment: {e}[/bold red]")
        raise typer.Exit(1)
    
    # Get paths to pip and python in the new venv
    if platform.system() == "Windows":
        pip_path = venv_path / "Scripts" / "pip.exe"
        python_path = venv_path / "Scripts" / "python.exe"
        activate_path = venv_path / "Scripts" / "activate.bat"
    else:
        pip_path = venv_path / "bin" / "pip"
        python_path = venv_path / "bin" / "python"
        activate_path = venv_path / "bin" / "activate"
    
    # Install dependencies based on environment type
    console.print("[bold blue]Installing dependencies...[/bold blue]")
    
    try:
        # Upgrade pip first
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)
        
        # Install wheel for binary packages
        subprocess.run([str(pip_path), "install", "wheel"], check=True)
        
        if env_type == EnvType.MINIMAL:
            # Install only core dependencies
            packages = [
                "typer", "flask==2.2.5", "werkzeug", "flask-cors", 
                "sqlalchemy", "psycopg2", "pgvector", "markdown"
            ]
            subprocess.run([str(pip_path), "install"] + packages, check=True)
            
        elif env_type == EnvType.MAC_OPTIMIZED:
            # Install dependencies with Mac optimizations
            is_apple_silicon = platform.machine() == "arm64"
            
            # Create Mac optimization file
            if is_apple_silicon:
                etc_dir = venv_path / "etc"
                etc_dir.mkdir(exist_ok=True)
                
                with open(etc_dir / "mac_optimizations.sh", "w") as f:
                    f.write("""# Mac-specific optimizations for Python environment
# Especially for Apple Silicon (M1/M2/M3)

# Memory optimizations for unified memory
export TCMALLOC_LARGE_ALLOC_REPORT_THRESHOLD=10000000000

# PyTorch MPS (Metal Performance Shaders) support
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Accelerate NumPy with Metal
export ACCELERATE_USE_SYSTEM=true

# OpenMP thread optimizations
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

# PostgreSQL optimizations
export PSYCOPG_IMPL=c
""")
                
                # Add source to activation script
                with open(activate_path, "a") as f:
                    f.write('\\nsource "$VIRTUAL_ENV/etc/mac_optimizations.sh"\\n')
            
            # Install core requirements in order to avoid conflicts
            packages = [
                "pydantic==1.10.21", "requests", "rich", 
                "flask==2.2.5", "werkzeug", "flask-cors",
                "sqlalchemy", "greenlet", "psycopg2", "pgvector",
                "typer", "click", "markdown", "python-dotenv",
                "keyring", "asgiref", "h11", "uvicorn==0.17.6",
                "pymdown-extensions"
            ]
            
            for package in packages:
                subprocess.run([str(pip_path), "install", package], check=True)
            
        else:  # STANDARD
            # Install from requirements.txt if it exists
            requirements_path = Path("requirements.txt")
            if requirements_path.exists():
                subprocess.run([str(pip_path), "install", "-r", str(requirements_path)], check=True)
            else:
                # Install core packages
                packages = [
                    "pydantic==1.10.21", "requests", "rich", 
                    "flask==2.2.5", "werkzeug", "flask-cors",
                    "sqlalchemy", "greenlet", "psycopg2", "pgvector",
                    "typer", "click", "markdown", "python-dotenv",
                    "keyring", "asgiref", "h11", "uvicorn==0.17.6",
                    "pymdown-extensions"
                ]
                subprocess.run([str(pip_path), "install"] + packages, check=True)
        
        # Install the package in development mode
        console.print("[bold blue]Installing carchive in development mode...[/bold blue]")
        subprocess.run([str(pip_path), "install", "-e", "."], check=True)
    
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to install dependencies: {e}[/bold red]")
        raise typer.Exit(1)
    
    # Create .env file if needed
    if not no_dotenv and not Path(".env").exists():
        console.print("[bold blue]Creating .env file...[/bold blue]")
        with open(".env", "w") as f:
            f.write("""# Database connection settings
# DB_USER=carchive_app
# DB_PASSWORD=your_password_here
# DB_HOST=localhost
# DB_NAME=carchive04_db

# External API settings
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here
OLLAMA_URL=http://localhost:11434

# Embedding settings
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text
EMBEDDING_DIMENSIONS=768

# Model settings
VISION_MODEL_NAME=llama3.2-vision
TEXT_MODEL_NAME=llama3.2
""")
    
    # Create run scripts
    if not no_run_scripts:
        console.print("[bold blue]Creating run scripts...[/bold blue]")
        
        script_suffix = env_type.value.replace("-", "_")
        
        # Create API server script
        api_script_path = Path(f"run_api_{script_suffix}.sh")
        with open(api_script_path, "w") as f:
            f.write(f"""#!/bin/bash
# Run the API server with {env_type} environment
source {venv_path}/bin/activate
echo "Starting API server..."
python api_server.py $@
""")
        
        # Create GUI server script
        gui_script_path = Path(f"run_gui_{script_suffix}.sh")
        with open(gui_script_path, "w") as f:
            f.write(f"""#!/bin/bash
# Run the GUI server with {env_type} environment
source {venv_path}/bin/activate
echo "Starting GUI server..."
python gui_server.py $@
""")
        
        # Make scripts executable on Unix
        if platform.system() != "Windows":
            os.chmod(api_script_path, 0o755)
            os.chmod(gui_script_path, 0o755)
    
    console.print("[bold green]Environment setup complete![/bold green]")
    
    if not no_run_scripts:
        console.print(f"To run the API server: ./run_api_{script_suffix}.sh")
        console.print(f"To run the GUI server: ./run_gui_{script_suffix}.sh")


@app.command()
def fix_dependencies():
    """
    Fix common dependency issues in the current environment.
    
    This replaces fix_dependencies.sh and install_missing_deps.sh.
    """
    console.print("[bold blue]Fixing dependencies in current environment...[/bold blue]")
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        console.print("[bold yellow]Warning: Not running in a virtual environment[/bold yellow]")
        proceed = typer.confirm("Proceed anyway?", default=False)
        if not proceed:
            raise typer.Exit(1)
    
    try:
        # Upgrade pip
        console.print("Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        
        # Install/reinstall key packages in the correct order
        packages = [
            "pydantic==1.10.21",  # Specific version to avoid conflicts
            "flask==2.2.5", "werkzeug",  # Flask with correct Werkzeug
            "pymdown-extensions",  # Markdown extensions
            "rich",  # Rich formatting
            "typer", "click",  # CLI tools
            "sqlalchemy", "greenlet", "psycopg2",  # Database
            "pgvector",  # Vector support
        ]
        
        for package in packages:
            console.print(f"Installing {package}...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", package], check=True)
        
        # Reinstall the project in development mode
        console.print("Reinstalling carchive in development mode...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True)
        
        console.print("[bold green]Dependencies fixed successfully![/bold green]")
    
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to fix dependencies: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def fix_cors():
    """
    Fix CORS settings for API and GUI servers.
    
    This replaces fix_cors.sh.
    """
    console.print("[bold blue]Fixing CORS settings...[/bold blue]")
    
    # Check if API server file exists
    api_file = Path("api_server.py")
    if not api_file.exists():
        console.print("[bold red]api_server.py not found[/bold red]")
        raise typer.Exit(1)
    
    # Read the current API server file
    with open(api_file, "r") as f:
        api_content = f.read()
    
    # Check if CORS is already configured
    if "CORS(" in api_content:
        if "origins=[" in api_content:
            console.print("CORS is already configured with origins")
        else:
            # Update the CORS configuration
            api_content = api_content.replace(
                "CORS(app)",
                "CORS(app, resources={r'/*': {'origins': '*'}})"
            )
            
            with open(api_file, "w") as f:
                f.write(api_content)
            
            console.print("[bold green]Updated CORS settings in api_server.py[/bold green]")
    else:
        # Add CORS import and configuration
        if "from flask_cors import CORS" not in api_content:
            api_content = api_content.replace(
                "from flask import Flask",
                "from flask import Flask\nfrom flask_cors import CORS"
            )
        
        # Add CORS initialization after app creation
        api_content = api_content.replace(
            "app = Flask(__name__)",
            "app = Flask(__name__)\nCORS(app, resources={r'/*': {'origins': '*'}})"
        )
        
        with open(api_file, "w") as f:
            f.write(api_content)
        
        console.print("[bold green]Added CORS configuration to api_server.py[/bold green]")
    
    # Similar check for GUI server if it exists
    gui_file = Path("gui_server.py")
    if gui_file.exists():
        with open(gui_file, "r") as f:
            gui_content = f.read()
        
        if "CORS(" in gui_content:
            if "origins=[" in gui_content:
                console.print("CORS is already configured in gui_server.py")
            else:
                # Update the CORS configuration
                gui_content = gui_content.replace(
                    "CORS(app)",
                    "CORS(app, resources={r'/*': {'origins': '*'}})"
                )
                
                with open(gui_file, "w") as f:
                    f.write(gui_content)
                
                console.print("[bold green]Updated CORS settings in gui_server.py[/bold green]")
        else:
            # Add CORS import and configuration
            if "from flask_cors import CORS" not in gui_content:
                gui_content = gui_content.replace(
                    "from flask import Flask",
                    "from flask import Flask\nfrom flask_cors import CORS"
                )
            
            # Add CORS initialization after app creation
            gui_content = gui_content.replace(
                "app = Flask(__name__)",
                "app = Flask(__name__)\nCORS(app, resources={r'/*': {'origins': '*'}})"
            )
            
            with open(gui_file, "w") as f:
                f.write(gui_content)
            
            console.print("[bold green]Added CORS configuration to gui_server.py[/bold green]")
    
    console.print("[bold green]CORS settings fixed successfully![/bold green]")


@app.command()
def check():
    """
    Check for common environment issues and suggest fixes.
    """
    issues = []
    suggestions = []
    
    # Check if running in virtual environment
    if sys.prefix == sys.base_prefix:
        issues.append("Not running in a virtual environment")
        suggestions.append("Create and activate a virtual environment with: carchive env setup")
    
    # Check for key packages
    try:
        import pkg_resources
        
        # Check pydantic version - specific version required
        try:
            pydantic_version = pkg_resources.get_distribution("pydantic").version
            if pydantic_version != "1.10.21":
                issues.append(f"Pydantic version mismatch: {pydantic_version} (should be 1.10.21)")
                suggestions.append("Fix dependencies with: carchive env fix-dependencies")
        except pkg_resources.DistributionNotFound:
            issues.append("Pydantic not installed")
            suggestions.append("Fix dependencies with: carchive env fix-dependencies")
        
        # Check flask version
        try:
            flask_version = pkg_resources.get_distribution("flask").version
            if not flask_version.startswith("2.2"):
                issues.append(f"Flask version mismatch: {flask_version} (should be 2.2.x)")
                suggestions.append("Fix dependencies with: carchive env fix-dependencies")
        except pkg_resources.DistributionNotFound:
            issues.append("Flask not installed")
            suggestions.append("Fix dependencies with: carchive env fix-dependencies")
        
        # Check for missing essential packages
        essential_packages = [
            "typer", "sqlalchemy", "psycopg2", "pgvector", 
            "rich", "markdown"
        ]
        
        missing_packages = []
        for package in essential_packages:
            try:
                pkg_resources.get_distribution(package)
            except pkg_resources.DistributionNotFound:
                missing_packages.append(package)
        
        if missing_packages:
            issues.append(f"Missing essential packages: {', '.join(missing_packages)}")
            suggestions.append("Fix dependencies with: carchive env fix-dependencies")
    
    except ImportError:
        issues.append("pkg_resources not available")
        suggestions.append("Reinstall setuptools with: pip install --upgrade setuptools")
    
    # Check for .env file
    if not Path(".env").exists():
        issues.append(".env file missing")
        suggestions.append("Create .env file with: carchive env setup --no-run-scripts")
    
    # Check API server for CORS configuration
    api_file = Path("api_server.py")
    if api_file.exists():
        with open(api_file, "r") as f:
            api_content = f.read()
        
        if "CORS(" not in api_content:
            issues.append("CORS not configured in api_server.py")
            suggestions.append("Fix CORS with: carchive env fix-cors")
    
    # Display results
    if issues:
        table = Table(title="Environment Issues Found")
        table.add_column("Issue", style="red")
        table.add_column("Suggestion", style="green")
        
        for i in range(len(issues)):
            table.add_row(issues[i], suggestions[i])
        
        console.print(table)
    else:
        console.print("[bold green]Environment check passed. No issues found.[/bold green]")