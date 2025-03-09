#!/bin/bash
# Wrapper script for carchive server management
# This script replaces the individual run_api.sh and run_gui.sh scripts
# as well as restart_servers.sh with a unified interface.

# Check for Python 3.10 environment
if [ -d "venv_310" ]; then
  source venv_310/bin/activate
  echo "Using Python 3.10 environment"
  
  # Verify rich is installed
  if ! python -c "import rich" 2>/dev/null; then
    echo "Installing missing 'rich' package..."
    pip install rich
  fi
  
  # Set PYTHONPATH
  export PYTHONPATH="$PWD/src:$PYTHONPATH"
fi

# Parse command line arguments
COMMAND="start"
SERVER_TYPE="both"
DEBUG=false
CORS="enhanced"
ENV_TYPE="mac-venv"
API_HOST="127.0.0.1"
API_PORT=8000
GUI_HOST="127.0.0.1"
GUI_PORT=8001

function show_help {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start servers (default)"
    echo "  stop        Stop servers"
    echo "  restart     Restart servers"
    echo "  status      Show server status"
    echo ""
    echo "Options:"
    echo "  --type, -t      Server type: api, gui, or both (default: both)"
    echo "  --debug, -d     Enable debug mode"
    echo "  --cors, -c      CORS configuration: standard, enhanced, or disabled (default: enhanced)"
    echo "  --env, -e       Environment type: standard, venv, mac-venv, or conda (default: mac-venv)"
    echo "  --api-host      API server host (default: 127.0.0.1)"
    echo "  --api-port      API server port (default: 8000)"
    echo "  --gui-host      GUI server host (default: 127.0.0.1)"
    echo "  --gui-port      GUI server port (default: 8001)"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                   # Start both servers with default settings"
    echo "  $0 start --type api --debug          # Start the API server in debug mode"
    echo "  $0 stop                              # Stop all servers"
    echo "  $0 restart --cors enhanced           # Restart servers with enhanced CORS"
    echo "  $0 status                            # Show server status"
    echo ""
    echo "This script uses the 'carchive server' CLI commands under the hood."
}

# Parse command argument
if [[ $# -gt 0 && ( "$1" == "start" || "$1" == "stop" || "$1" == "restart" || "$1" == "status" ) ]]; then
    COMMAND="$1"
    shift
fi

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --type|-t)
            SERVER_TYPE="$2"
            shift 2
            ;;
        --debug|-d)
            DEBUG=true
            shift
            ;;
        --cors|-c)
            CORS="$2"
            shift 2
            ;;
        --env|-e)
            ENV_TYPE="$2"
            shift 2
            ;;
        --api-host)
            API_HOST="$2"
            shift 2
            ;;
        --api-port)
            API_PORT="$2"
            shift 2
            ;;
        --gui-host)
            GUI_HOST="$2"
            shift 2
            ;;
        --gui-port)
            GUI_PORT="$2"
            shift 2
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Convert environment type to CLI format
case "$ENV_TYPE" in
    standard)
        ENV_CLI="standard"
        ;;
    venv)
        ENV_CLI="venv"
        ;;
    mac-venv)
        ENV_CLI="mac-venv"
        ;;
    conda)
        ENV_CLI="conda"
        ;;
    *)
        ENV_CLI="mac-venv"
        ;;
esac

# Build the command to execute
CMD_PREFIX="poetry run carchive server"

case "$COMMAND" in
    start)
        if [ "$SERVER_TYPE" == "api" ]; then
            CMD="$CMD_PREFIX start-api --host $API_HOST --port $API_PORT --env-type $ENV_CLI --cors $CORS"
            if [ "$DEBUG" == "true" ]; then
                CMD="$CMD --debug"
            fi
        elif [ "$SERVER_TYPE" == "gui" ]; then
            CMD="$CMD_PREFIX start-gui --host $GUI_HOST --port $GUI_PORT --api-url http://$API_HOST:$API_PORT --env-type $ENV_CLI --cors $CORS"
            if [ "$DEBUG" == "true" ]; then
                CMD="$CMD --debug"
            fi
        else
            CMD="$CMD_PREFIX start-all --api-host $API_HOST --api-port $API_PORT --gui-host $GUI_HOST --gui-port $GUI_PORT --env-type $ENV_CLI --cors $CORS"
            if [ "$DEBUG" == "true" ]; then
                CMD="$CMD --debug"
            fi
        fi
        ;;
    stop)
        CMD="$CMD_PREFIX stop --type $SERVER_TYPE --api-port $API_PORT --gui-port $GUI_PORT"
        ;;
    restart)
        CMD="$CMD_PREFIX restart --type $SERVER_TYPE --api-host $API_HOST --api-port $API_PORT --gui-host $GUI_HOST --gui-port $GUI_PORT --env-type $ENV_CLI --cors $CORS"
        if [ "$DEBUG" == "true" ]; then
            CMD="$CMD --debug"
        fi
        ;;
    status)
        CMD="$CMD_PREFIX status"
        ;;
esac

# Execute the command
eval "$CMD"