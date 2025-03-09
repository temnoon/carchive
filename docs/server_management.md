# Carchive Server Management Guide

This guide covers the server management features in carchive, including starting, stopping, and configuring API and GUI servers.

## Overview

Carchive provides a unified CLI interface for managing servers with the `carchive server` command. This replaces multiple shell scripts and provides consistent functionality across platforms.

The system consists of two main components:
1. **API Server** (port 8000): Provides REST API endpoints for accessing and manipulating data
2. **GUI Server** (port 8001): Provides a web interface for user interaction

## Quick Start

The simplest way to start both servers with standard configuration:

```bash
./run_servers_8000_8001.sh
```

This will start the API server on port 8000 and the GUI server on port 8001 with the appropriate configuration.

## Server Commands

### Checking Server Status

```bash
# Display the status of all servers
poetry run carchive server status
```

This shows the current status of the API and GUI servers, including their running processes and ports.

### Starting Servers

```bash
# Start the API server
poetry run carchive server start-api

# Start the GUI server
poetry run carchive server start-gui

# Start both servers
poetry run carchive server start-all
```

Each command supports various options for customizing the server configuration.

### Stopping Servers

```bash
# Stop the API server
poetry run carchive server stop --type api

# Stop the GUI server
poetry run carchive server stop --type gui

# Stop all servers
poetry run carchive server stop
```

### Restarting Servers

```bash
# Restart the API server
poetry run carchive server restart --type api

# Restart the GUI server
poetry run carchive server restart --type gui

# Restart all servers
poetry run carchive server restart
```

### Creating Shell Scripts

```bash
# Create custom shell scripts for your server configuration
poetry run carchive server create-run-script
```

This generates shell scripts that can be used to start the servers with your specified configuration.

## Configuration Options

### API Server Options

```bash
poetry run carchive server start-api --help
```

Key options include:
- `--host, -H`: Host to bind to (default: 127.0.0.1)
- `--port, -p`: Port to bind to (default: 8000)
- `--env-type, -e`: Environment to use (standard, venv, mac-venv, conda)
- `--cors, -c`: CORS configuration (standard, enhanced, disabled)
- `--debug, -d`: Enable debug mode
- `--foreground, -f`: Run in foreground (blocking)

### GUI Server Options

```bash
poetry run carchive server start-gui --help
```

Key options include:
- `--host, -H`: Host to bind to (default: 127.0.0.1)
- `--port, -p`: Port to bind to (default: 8001)
- `--api-url, -a`: URL for the API server (default: http://127.0.0.1:8000)
- `--env-type, -e`: Environment to use
- `--cors, -c`: CORS configuration
- `--debug, -d`: Enable debug mode
- `--foreground, -f`: Run in foreground (blocking)

## Shell Scripts

For convenience, several shell scripts are provided:

### API Server Scripts

- `run_api_8000.sh`: Run the API server on port 8000
  ```bash
  ./run_api_8000.sh
  ```

### GUI Server Scripts

- `run_gui_8001.sh`: Run the GUI server on port 8001
  ```bash
  ./run_gui_8001.sh
  ```

### Combined Scripts

- `run_servers_8000_8001.sh`: Run both API and GUI servers on ports 8000 and 8001
  ```bash
  ./run_servers_8000_8001.sh
  ```

- `run_servers.sh`: Wrapper script for the CLI with more options
  ```bash
  # Basic usage (starts both servers on 8000/8001)
  ./run_servers.sh
  
  # Start only the API server
  ./run_servers.sh start --type api
  
  # Start with debugging enabled
  ./run_servers.sh start --debug
  
  # Stop all servers
  ./run_servers.sh stop
  
  # Check server status
  ./run_servers.sh status
  ```

## Environment Types

The server commands support different environment types:

### Standard Environment

The default Python virtual environment at `./venv`.

```bash
poetry run carchive server start-all --env-type standard
```

### Mac-Optimized Environment

A Mac-specific environment at `./mac_venv`.

```bash
poetry run carchive server start-all --env-type mac-venv
```

### Conda Environment

For conda users, uses the active conda environment.

```bash
poetry run carchive server start-all --env-type conda
```

## CORS Configurations

Three CORS configurations are available:

### Standard CORS

Basic CORS configuration suitable for most uses.

```bash
poetry run carchive server start-all --cors standard
```

### Enhanced CORS

More permissive CORS configuration for advanced use cases.

```bash
poetry run carchive server start-all --cors enhanced
```

### Disabled CORS

Turn off CORS for local development.

```bash
poetry run carchive server start-all --cors disabled
```

## Common Use Cases

### Starting Development Servers

```bash
poetry run carchive server start-all --debug --cors enhanced
```

### Production Configuration

```bash
poetry run carchive server start-all --host 0.0.0.0 --env-type mac-venv --cors standard
```

### Custom Port Configuration

```bash
poetry run carchive server start-all --api-port 8000 --gui-port 8001
```

## Port Standardization

As part of the codebase standardization, we have moved to consistent port usage:

- **API Server**: Port 8000 (previously 5000)
- **GUI Server**: Port 8001 (previously 5001)

All scripts and commands now default to these ports. If you need to use the old ports or custom ports, you can specify them explicitly with the `--api-port` and `--gui-port` options.

## Legacy Scripts

The following legacy shell scripts have been replaced by the `carchive server` command:

- `run_api.sh` → `carchive server start-api`
- `run_api_fixed.sh` → `carchive server start-api --env-type mac-venv`
- `run_api_with_cors.sh` → `carchive server start-api --cors enhanced`
- `run_gui.sh` → `carchive server start-gui`
- `run_gui_fixed.sh` → `carchive server start-gui --env-type mac-venv`
- `run_gui_with_cors.sh` → `carchive server start-gui --cors enhanced`
- `restart_servers.sh` → `carchive server restart`

New standardized scripts have been created:
- `run_api_8000.sh`: Run the API server on port 8000
- `run_gui_8001.sh`: Run the GUI server on port 8001
- `run_servers_8000_8001.sh`: Run both servers on standardized ports

## Troubleshooting

### Port Already in Use

If you see an error message indicating a port is already in use:

```bash
# Check the status of servers
poetry run carchive server status

# Stop any running servers
poetry run carchive server stop

# Start with a different port
poetry run carchive server start-api --port 8080
```

### Environment Issues

If you encounter problems with the Python environment:

```bash
# Verify environment setup
poetry run carchive env check

# Fix environment issues and retry
poetry run carchive env fix-dependencies
poetry run carchive server start-all
```

### CORS Issues

If you encounter CORS errors when accessing the API from web clients:

```bash
# Use enhanced CORS configuration
poetry run carchive server restart --cors enhanced
```

## Advanced Configuration

For advanced configuration, environment variables can be set:

- `CARCHIVE_DB_URI`: Database connection string
- `CARCHIVE_MEDIA_DIR`: Media storage directory
- `CARCHIVE_API_URL`: URL for API (used by GUI)
- `FLASK_DEBUG`: Enable debug mode (1) or disable (0)
- `CARCHIVE_CORS_ENABLED`: Enable CORS support

Example:

```bash
export CARCHIVE_DB_URI="postgresql://user:pass@localhost/dbname"
export CARCHIVE_MEDIA_DIR="/path/to/media"
./run_api_8000.sh
```

## Integration with Other Commands

The server management commands integrate well with other carchive features:

```bash
# Complete setup and server launch workflow
poetry run carchive env setup
poetry run carchive db validate
poetry run carchive server start-all
```

## Security Considerations

- For production use, consider using proper SSL/TLS termination
- Restrict server binding to appropriate interfaces (not 0.0.0.0 for public access)
- Use environment-specific CORS settings
- Consider using a reverse proxy like Nginx for additional security

## FAQs

### Q: When should I use blocking vs. non-blocking mode?
A: Use blocking mode (`--foreground`) when you want to see real-time server logs in the terminal. Use non-blocking (default) when you want to start the server in the background.

### Q: How do I change the API URL the GUI connects to?
A: Use `--api-url` when starting the GUI server: `carchive server start-gui --api-url http://custom-api:8000`

### Q: Can I run the servers on a different network interface?
A: Yes, use `--host 0.0.0.0` to bind to all interfaces or specify a particular IP.

### Q: Why have the default ports changed from 5000/5001 to 8000/8001?
A: The port standardization is part of the overall architecture standardization effort. Ports 8000/8001 are less likely to conflict with other development services and provide consistency across deployments.