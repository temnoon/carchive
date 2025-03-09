"""
Server management CLI for carchive.

This module provides commands for starting, stopping, and managing the API and GUI servers.
It consolidates various run_*.sh scripts into a unified interface.
"""

import os
import sys
import signal
import logging
import platform
import subprocess
import time
from pathlib import Path
from enum import Enum
from typing import List, Optional, Dict, Any

import typer
import psutil
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress

# Configure logger
logger = logging.getLogger(__name__)
console = Console()

# Create Typer app
app = typer.Typer(help="Server management commands")


class ServerType(str, Enum):
    """Types of servers that can be managed."""
    API = "api"
    GUI = "gui"
    BOTH = "both"


class EnvType(str, Enum):
    """Types of environments to use."""
    STANDARD = "standard"
    VENV = "venv"
    MAC_VENV = "mac-venv"
    CONDA = "conda"


class CorsMode(str, Enum):
    """CORS configuration options."""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    DISABLED = "disabled"


def get_processes_using_port(port: int) -> List[int]:
    """Find process IDs using the specified port."""
    pids = []
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            connections = proc.connections()
            for conn in connections:
                if conn.laddr.port == port:
                    pids.append(proc.pid)
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return pids


def kill_processes_using_port(port: int) -> List[int]:
    """Kill processes using the specified port."""
    killed_pids = []
    pids = get_processes_using_port(port)
    for pid in pids:
        try:
            process = psutil.Process(pid)
            process.terminate()
            killed_pids.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    # If processes are still running after 3 seconds, force kill
    if killed_pids:
        time.sleep(3)
        for pid in killed_pids:
            try:
                process = psutil.Process(pid)
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    return killed_pids


def is_server_running(port: int) -> bool:
    """Check if a server is running on the specified port."""
    # First check if the port is in use with psutil
    has_process = len(get_processes_using_port(port)) > 0
    
    # If process found, also try to connect to verify it's responding
    if has_process:
        import socket
        try:
            # Create a socket object
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Set a timeout of 1 second
            s.settimeout(1)
            # Try to connect to the port
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            # If result is 0, connection was successful
            return result == 0
        except:
            pass
    
    return has_process


def get_environment_path(env_type: EnvType) -> Path:
    """Get the path to the specified environment."""
    base_dir = Path(os.getcwd())
    
    if env_type == EnvType.STANDARD:
        return base_dir / "venv"
    elif env_type == EnvType.VENV:
        return base_dir / "venv"
    elif env_type == EnvType.MAC_VENV:
        return base_dir / "mac_venv"
    elif env_type == EnvType.CONDA:
        return Path(os.environ.get("CONDA_PREFIX", "conda_env"))
    
    return base_dir / "venv"


def get_python_path(env_type: EnvType) -> Path:
    """Get the path to the Python executable in the specified environment."""
    env_path = get_environment_path(env_type)
    
    if platform.system() == "Windows":
        python_path = env_path / "Scripts" / "python.exe"
    else:
        python_path = env_path / "bin" / "python"
    
    # First try to find Python 3.10 in the environment
    python310_path = None
    if platform.system() == "Windows":
        if (env_path / "Scripts" / "python3.10.exe").exists():
            python310_path = env_path / "Scripts" / "python3.10.exe"
    else:
        if (env_path / "bin" / "python3.10").exists():
            python310_path = env_path / "bin" / "python3.10"
    
    # If Python 3.10 is found, use it
    if python310_path is not None:
        console.print(f"[green]Using Python 3.10 at {python310_path}[/green]")
        return python310_path
    
    # Otherwise, try the default python in the environment
    if not python_path.exists():
        console.print(f"[yellow]Warning: Python executable not found at {python_path}[/yellow]")
        console.print(f"[yellow]Falling back to system Python[/yellow]")
        python_path = Path(sys.executable)
    
    # Print warning if not using Python 3.10
    try:
        python_version = subprocess.check_output([str(python_path), "-V"], 
                                                text=True, stderr=subprocess.STDOUT)
        if "3.10" not in python_version:
            console.print(f"[yellow]Warning: Using {python_version.strip()}. " +
                         "This project is designed for Python 3.10.[/yellow]")
    except Exception:
        pass
    
    return python_path


def get_activate_command(env_type: EnvType) -> str:
    """Get the command to activate the specified environment."""
    env_path = get_environment_path(env_type)
    
    if platform.system() == "Windows":
        if env_type == EnvType.CONDA:
            return f"conda activate {env_path.name}"
        else:
            return str(env_path / "Scripts" / "activate")
    else:
        if env_type == EnvType.CONDA:
            return f"conda activate {env_path.name}"
        else:
            return f"source {env_path}/bin/activate"


def generate_config_for_server(
    server_type: ServerType,
    cors_mode: CorsMode,
    api_url: Optional[str] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    """Generate configuration for the specified server."""
    config = {
        "DEBUG": debug
    }
    
    if server_type == ServerType.GUI and api_url:
        config["API_URL"] = api_url
    
    if cors_mode == CorsMode.ENHANCED:
        config["CORS_ENABLED"] = True
        config["CORS_ALLOW_ALL"] = True
    elif cors_mode == CorsMode.STANDARD:
        config["CORS_ENABLED"] = True
        config["CORS_ALLOW_ALL"] = False
    else:
        config["CORS_ENABLED"] = False
    
    return config


def create_server_script(
    server_type: ServerType,
    host: str,
    port: int,
    env_type: EnvType,
    cors_mode: CorsMode,
    api_url: Optional[str] = None,
    debug: bool = False,
) -> str:
    """Create a Python script to run the specified server."""
    config = generate_config_for_server(server_type, cors_mode, api_url, debug)
    
    config_str = ", ".join([f"'{k}': {repr(v)}" for k, v in config.items()])
    
    if server_type == ServerType.API:
        script = f"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('__file__')), 'src'))
from carchive.api import create_app

app = create_app({{{config_str}}})
"""
        if cors_mode == CorsMode.ENHANCED:
            script += """
from flask_cors import CORS
CORS(app, resources={r'/*': {'origins': '*', 'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], 'allow_headers': '*'}})
"""
        script += f"""
print(f"Starting API server at http://{host}:{port}")
app.run(host='{host}', port={port}, debug={debug})
"""
    else:  # GUI
        script = f"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('__file__')), 'src'))
from carchive.gui import create_app

app = create_app({{{config_str}}})
print(f"Starting GUI server at http://{host}:{port}")
"""
        if api_url:
            script += f'print(f"API URL: {api_url}")\n'
        script += f"app.run(host='{host}', port={port}, debug={debug})"
    
    return script


@app.command()
def status():
    """
    Display the status of the API and GUI servers.
    """
    table = Table(title="Server Status")
    table.add_column("Server", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Port", style="blue")
    table.add_column("PID", style="yellow")
    
    # Check API server (port 8000)
    api_pids = get_processes_using_port(8000)
    api_status = "Running" if api_pids else "Stopped"
    api_pid = str(api_pids[0]) if api_pids else "N/A"
    table.add_row("API", api_status, "8000", api_pid)
    
    # Check GUI server (port 8001)
    gui_pids = get_processes_using_port(8001)
    gui_status = "Running" if gui_pids else "Stopped"
    gui_pid = str(gui_pids[0]) if gui_pids else "N/A"
    table.add_row("GUI", gui_status, "8001", gui_pid)
    
    console.print(table)


@app.command()
def start_api(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Host to bind to."),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to."),
    env_type: EnvType = typer.Option(EnvType.MAC_VENV, "--env-type", "-e", help="Environment to use."),
    cors_mode: CorsMode = typer.Option(CorsMode.ENHANCED, "--cors", "-c", help="CORS configuration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground (blocking)."),
):
    """
    Start the API server.
    """
    # Check if server is already running
    if is_server_running(port):
        console.print(f"[yellow]Warning: Server already running on port {port}[/yellow]")
        if typer.confirm("Do you want to stop it and start a new instance?"):
            kill_processes_using_port(port)
        else:
            return
    
    # Create a temporary script file
    script = create_server_script(
        ServerType.API,
        host,
        port,
        env_type,
        cors_mode,
        debug=debug
    )
    
    temp_script_path = Path("temp_api_server.py")
    with open(temp_script_path, "w") as f:
        f.write(script)
    
    try:
        # Get Python path - prioritize the active environment's Python
        if "VIRTUAL_ENV" in os.environ:
            # Use the Python from the active virtual environment
            console.print(f"[green]Using Python from active virtual environment: {os.environ['VIRTUAL_ENV']}[/green]")
            if platform.system() == "Windows":
                python_path = Path(os.environ["VIRTUAL_ENV"]) / "Scripts" / "python.exe"
            else:
                python_path = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
        else:
            # Fall back to the configured environment
            python_path = get_python_path(env_type)
        
        # Print Python version
        try:
            python_version = subprocess.check_output([str(python_path), "-V"], 
                                               text=True, stderr=subprocess.STDOUT).strip()
            console.print(f"[green]Using {python_version}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not determine Python version: {e}[/yellow]")
        
        # Run the server
        command = [str(python_path), str(temp_script_path)]
        
        if foreground:
            # Run in foreground (blocking)
            subprocess.run(command)
        else:
            # Run in background
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to check if the process started successfully
            time.sleep(2)
            if proc.poll() is not None:
                # Process exited
                stdout, stderr = proc.communicate()
                console.print(f"[red]Error: API server failed to start[/red]")
                console.print(f"[red]stdout: {stdout}[/red]")
                console.print(f"[red]stderr: {stderr}[/red]")
            else:
                console.print(f"[green]API server started successfully on http://{host}:{port}[/green]")
    finally:
        # Clean up the temporary script
        if temp_script_path.exists():
            temp_script_path.unlink()


@app.command()
def start_gui(
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Host to bind to."),
    port: int = typer.Option(8001, "--port", "-p", help="Port to bind to."),
    api_url: str = typer.Option("http://127.0.0.1:8000", "--api-url", "-a", help="URL for the API server."),
    env_type: EnvType = typer.Option(EnvType.MAC_VENV, "--env-type", "-e", help="Environment to use."),
    cors_mode: CorsMode = typer.Option(CorsMode.STANDARD, "--cors", "-c", help="CORS configuration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground (blocking)."),
):
    """
    Start the GUI server.
    """
    # Check if server is already running
    if is_server_running(port):
        console.print(f"[yellow]Warning: Server already running on port {port}[/yellow]")
        if typer.confirm("Do you want to stop it and start a new instance?"):
            kill_processes_using_port(port)
        else:
            return
    
    # Create a temporary script file
    script = create_server_script(
        ServerType.GUI,
        host,
        port,
        env_type,
        cors_mode,
        api_url=api_url,
        debug=debug
    )
    
    temp_script_path = Path("temp_gui_server.py")
    with open(temp_script_path, "w") as f:
        f.write(script)
    
    try:
        # Get Python path - prioritize the active environment's Python
        if "VIRTUAL_ENV" in os.environ:
            # Use the Python from the active virtual environment
            console.print(f"[green]Using Python from active virtual environment: {os.environ['VIRTUAL_ENV']}[/green]")
            if platform.system() == "Windows":
                python_path = Path(os.environ["VIRTUAL_ENV"]) / "Scripts" / "python.exe"
            else:
                python_path = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python"
        else:
            # Fall back to the configured environment
            python_path = get_python_path(env_type)
        
        # Print Python version
        try:
            python_version = subprocess.check_output([str(python_path), "-V"], 
                                               text=True, stderr=subprocess.STDOUT).strip()
            console.print(f"[green]Using {python_version}[/green]")
        except Exception as e:
            console.print(f"[yellow]Could not determine Python version: {e}[/yellow]")
        
        # Run the server
        command = [str(python_path), str(temp_script_path)]
        
        if foreground:
            # Run in foreground (blocking)
            subprocess.run(command)
        else:
            # Run in background
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to check if the process started successfully
            time.sleep(2)
            if proc.poll() is not None:
                # Process exited
                stdout, stderr = proc.communicate()
                console.print(f"[red]Error: GUI server failed to start[/red]")
                console.print(f"[red]stdout: {stdout}[/red]")
                console.print(f"[red]stderr: {stderr}[/red]")
            else:
                console.print(f"[green]GUI server started successfully on http://{host}:{port}[/green]")
                console.print(f"[green]Connected to API at {api_url}[/green]")
    finally:
        # Clean up the temporary script
        if temp_script_path.exists():
            temp_script_path.unlink()


@app.command()
def start_all(
    api_host: str = typer.Option("127.0.0.1", "--api-host", help="Host for the API server."),
    api_port: int = typer.Option(8000, "--api-port", help="Port for the API server."),
    gui_host: str = typer.Option("127.0.0.1", "--gui-host", help="Host for the GUI server."),
    gui_port: int = typer.Option(8001, "--gui-port", help="Port for the GUI server."),
    env_type: EnvType = typer.Option(EnvType.MAC_VENV, "--env-type", "-e", help="Environment to use."),
    cors_mode: CorsMode = typer.Option(CorsMode.ENHANCED, "--cors", "-c", help="CORS configuration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
):
    """
    Start both API and GUI servers.
    """
    # Check if servers are already running
    api_running = is_server_running(api_port)
    gui_running = is_server_running(gui_port)
    
    if api_running or gui_running:
        console.print("[yellow]Warning: One or more servers are already running[/yellow]")
        if typer.confirm("Do you want to stop them and start new instances?"):
            if api_running:
                kill_processes_using_port(api_port)
            if gui_running:
                kill_processes_using_port(gui_port)
        else:
            return
    
    # Start API server
    console.print("[cyan]Starting API server...[/cyan]")
    start_api(
        host=api_host,
        port=api_port,
        env_type=env_type,
        cors_mode=cors_mode,
        debug=debug,
        foreground=False
    )
    
    # Short delay to ensure API is up
    time.sleep(2)
    
    # Verify API started successfully
    if not is_server_running(api_port):
        console.print("[red]Error: API server failed to start or is not responding[/red]")
        return
    
    # Start GUI server
    console.print("[cyan]Starting GUI server...[/cyan]")
    start_gui(
        host=gui_host,
        port=gui_port,
        api_url=f"http://{api_host}:{api_port}",
        env_type=env_type,
        cors_mode=cors_mode,
        debug=debug,
        foreground=False
    )
    
    # Verify GUI started successfully
    time.sleep(2)
    if not is_server_running(gui_port):
        console.print("[red]Error: GUI server failed to start or is not responding[/red]")
        return
    
    # Both servers started successfully
    console.print(f"\n[green]Servers started successfully![/green]")
    console.print(f"[green]API server: http://{api_host}:{api_port}[/green]")
    console.print(f"[green]GUI server: http://{gui_host}:{gui_port}[/green]")
    console.print(f"[green]You can access the web interface by opening http://{gui_host}:{gui_port} in your browser.[/green]")


@app.command()
def stop(
    server_type: ServerType = typer.Option(ServerType.BOTH, "--type", "-t", help="Server type to stop."),
    api_port: int = typer.Option(8000, "--api-port", help="Port for the API server."),
    gui_port: int = typer.Option(8001, "--gui-port", help="Port for the GUI server."),
):
    """
    Stop running servers.
    """
    if server_type in [ServerType.API, ServerType.BOTH]:
        console.print(f"[cyan]Stopping API server on port {api_port}...[/cyan]")
        pids = kill_processes_using_port(api_port)
        if pids:
            console.print(f"[green]Stopped API server process(es): {', '.join(map(str, pids))}[/green]")
        else:
            console.print(f"[yellow]No API server running on port {api_port}[/yellow]")
    
    if server_type in [ServerType.GUI, ServerType.BOTH]:
        console.print(f"[cyan]Stopping GUI server on port {gui_port}...[/cyan]")
        pids = kill_processes_using_port(gui_port)
        if pids:
            console.print(f"[green]Stopped GUI server process(es): {', '.join(map(str, pids))}[/green]")
        else:
            console.print(f"[yellow]No GUI server running on port {gui_port}[/yellow]")


@app.command()
def restart(
    server_type: ServerType = typer.Option(ServerType.BOTH, "--type", "-t", help="Server type to restart."),
    api_host: str = typer.Option("127.0.0.1", "--api-host", help="Host for the API server."),
    api_port: int = typer.Option(8000, "--api-port", help="Port for the API server."),
    gui_host: str = typer.Option("127.0.0.1", "--gui-host", help="Host for the GUI server."),
    gui_port: int = typer.Option(8001, "--gui-port", help="Port for the GUI server."),
    env_type: EnvType = typer.Option(EnvType.MAC_VENV, "--env-type", "-e", help="Environment to use."),
    cors_mode: CorsMode = typer.Option(CorsMode.ENHANCED, "--cors", "-c", help="CORS configuration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
):
    """
    Restart running servers.
    """
    # First stop the servers
    stop(server_type, api_port, gui_port)
    
    # Give processes time to fully terminate
    time.sleep(2)
    
    # Then start them again
    if server_type in [ServerType.API, ServerType.BOTH]:
        console.print(f"[cyan]Starting API server...[/cyan]")
        start_api(
            host=api_host,
            port=api_port,
            env_type=env_type,
            cors_mode=cors_mode,
            debug=debug,
            foreground=False
        )
    
    # Short delay if starting both
    if server_type == ServerType.BOTH:
        time.sleep(2)
    
    if server_type in [ServerType.GUI, ServerType.BOTH]:
        console.print(f"[cyan]Starting GUI server...[/cyan]")
        start_gui(
            host=gui_host,
            port=gui_port,
            api_url=f"http://{api_host}:{api_port}",
            env_type=env_type,
            cors_mode=cors_mode,
            debug=debug,
            foreground=False
        )


@app.command()
def create_run_script(
    server_type: ServerType = typer.Option(ServerType.BOTH, "--type", "-t", help="Server type to create script for."),
    api_host: str = typer.Option("127.0.0.1", "--api-host", help="Host for the API server."),
    api_port: int = typer.Option(8000, "--api-port", help="Port for the API server."),
    gui_host: str = typer.Option("127.0.0.1", "--gui-host", help="Host for the GUI server."),
    gui_port: int = typer.Option(8001, "--gui-port", help="Port for the GUI server."),
    env_type: EnvType = typer.Option(EnvType.MAC_VENV, "--env-type", "-e", help="Environment to use."),
    cors_mode: CorsMode = typer.Option(CorsMode.ENHANCED, "--cors", "-c", help="CORS configuration."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
    output_dir: Path = typer.Option(Path.cwd(), "--output-dir", "-o", help="Directory to save scripts."),
):
    """
    Create shell scripts to start servers with the specified configuration.
    """
    activate_cmd = get_activate_command(env_type)
    
    if server_type in [ServerType.API, ServerType.BOTH]:
        script_path = output_dir / "run_api_custom.sh"
        with open(script_path, "w") as f:
            f.write(f"""#!/bin/bash
# Generated API server script
{activate_cmd}
export FLASK_DEBUG={1 if debug else 0}
python -c "
{create_server_script(ServerType.API, api_host, api_port, env_type, cors_mode, debug=debug)}
" "$@"
""")
        os.chmod(script_path, 0o755)
        console.print(f"[green]Created API server script: {script_path}[/green]")
    
    if server_type in [ServerType.GUI, ServerType.BOTH]:
        script_path = output_dir / "run_gui_custom.sh"
        with open(script_path, "w") as f:
            f.write(f"""#!/bin/bash
# Generated GUI server script
{activate_cmd}
export FLASK_DEBUG={1 if debug else 0}
python -c "
{create_server_script(ServerType.GUI, gui_host, gui_port, env_type, cors_mode, api_url=f'http://{api_host}:{api_port}', debug=debug)}
" "$@"
""")
        os.chmod(script_path, 0o755)
        console.print(f"[green]Created GUI server script: {script_path}[/green]")
    
    if server_type == ServerType.BOTH:
        restart_script_path = output_dir / "restart_servers_custom.sh"
        with open(restart_script_path, "w") as f:
            f.write(f"""#!/bin/bash
# Generated restart script for both servers

echo "Restarting API and GUI servers..."

# Kill any processes using ports {api_port} and {gui_port}
echo "Stopping any processes using ports {api_port} and {gui_port}..."

# Check for processes using port {api_port} (API)
API_PIDS=$(lsof -ti:{api_port})
if [ ! -z "$API_PIDS" ]; then
    echo "Killing processes using port {api_port}: $API_PIDS"
    kill -9 $API_PIDS 2>/dev/null || true
fi

# Check for processes using port {gui_port} (GUI)
GUI_PIDS=$(lsof -ti:{gui_port})
if [ ! -z "$GUI_PIDS" ]; then
    echo "Killing processes using port {gui_port}: $GUI_PIDS"
    kill -9 $GUI_PIDS 2>/dev/null || true
fi

# Also find Flask processes more broadly
FLASK_PIDS=$(pgrep -f "python.*flask run")
if [ ! -z "$FLASK_PIDS" ]; then
    echo "Killing Flask processes: $FLASK_PIDS"
    kill -9 $FLASK_PIDS 2>/dev/null || true
fi

# Give processes time to fully terminate
sleep 2

# Start the servers
echo "Starting API server..."
./run_api_custom.sh &
API_PID=$!

# Wait a moment for the API server to start
sleep 2

echo "Starting GUI server..."
./run_gui_custom.sh &
GUI_PID=$!

echo "Servers restarted!"
echo "API server running at http://{api_host}:{api_port}"
echo "GUI server running at http://{gui_host}:{gui_port}"
echo ""
echo "You can access the web interface by opening http://{gui_host}:{gui_port} in your browser."
""")
        os.chmod(restart_script_path, 0o755)
        console.print(f"[green]Created restart script: {restart_script_path}[/green]")