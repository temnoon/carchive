#!/bin/bash
# Source this file to activate the correct environment for carchive
# Usage: source activate.sh

# Load environment variables from .env file
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
  echo "Loaded environment variables from .env"
fi

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Determine the best available Python 3.10 environment
if [ -d "venv_310" ]; then
  source venv_310/bin/activate
  echo "Activated Python 3.10 environment (venv_310)"
  export PYTHONPATH="$PWD/src:$PYTHONPATH"
elif command_exists conda && conda env list | grep -q "carchive-py3.10"; then
  source $(conda info --base)/etc/profile.d/conda.sh
  conda activate carchive-py3.10
  echo "Activated conda environment (carchive-py3.10)"
  export PYTHONPATH="$PWD/src:$PYTHONPATH"
else
  echo "Warning: No Python 3.10 environment found."
  echo "You should create a Python 3.10 environment with:"
  echo "  python3.10 -m venv venv_310"
  echo "  source venv_310/bin/activate"
  echo "  pip install -e ."
  
  # Fallback to any available environment, with warning
  if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Fallback: Activated standard venv environment"
    python_version=$(python --version)
    echo "Current Python version: $python_version (note: project requires Python 3.10)"
  elif [ -d "mac_venv" ]; then
    source mac_venv/bin/activate
    echo "Fallback: Activated mac_venv environment"
    python_version=$(python --version)
    echo "Current Python version: $python_version (note: project requires Python 3.10)"
  fi
  export PYTHONPATH="$PWD/src:$PYTHONPATH"
fi

# Verify the active Python version
echo -n "Active Python version: "
python --version

# Check for crucial dependencies
echo "Checking critical dependencies..."
missing_deps=0

check_dependency() {
  if ! python -c "import $1" 2>/dev/null; then
    echo "❌ $1 is missing"
    missing_deps=$((missing_deps + 1))
    return 1
  else
    echo "✅ $1 is installed"
    return 0
  fi
}

# Set correct PYTHONPATH
export PYTHONPATH="$PWD/src:$PYTHONPATH"

check_dependency flask
check_dependency flask_cors
check_dependency sqlalchemy
check_dependency pydantic
check_dependency typer
check_dependency rich
check_dependency httpx

if [ "$missing_deps" -gt 0 ]; then
  echo ""
  echo "Missing dependencies detected. Would you like to install them? (y/n)"
  read -r response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    pip install -e .
  else
    echo "You can install dependencies later with: pip install -e ."
  fi
fi

# Set up aliases for common commands
alias carchive-api="python api_server.py --port 8000"
alias carchive-gui="python gui_server.py --port 8001 --api-url http://localhost:8000"
alias carchive-start-all="./run_servers.sh"
alias carchive-status="carchive server status"

echo ""
echo "Environment activated successfully!"
echo "Available commands:"
echo "  - carchive-api: Start the API server"
echo "  - carchive-gui: Start the GUI server"
echo "  - carchive-start-all: Start both servers"
echo "  - carchive-status: Check server status"
echo ""
echo "To start servers with the recommended configuration:"
echo "  ./run_servers.sh"