#!/bin/bash
# Fixed version of the server script that ensures proper environment activation

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Detect and activate the most appropriate environment
if [ -d "mac_venv" ]; then
  echo "Activating mac_venv environment..."
  source mac_venv/bin/activate
elif [ -d "venv" ]; then
  echo "Activating venv environment..."
  source venv/bin/activate
elif [ -d "venv_310" ]; then
  echo "Activating venv_310 environment..."
  source venv_310/bin/activate
elif command_exists conda; then
  echo "Activating conda environment..."
  # This requires conda init to be run in the shell
  conda activate carchive-py3.10 2>/dev/null || conda activate base
else
  echo "WARNING: No virtual environment found. Using system Python."
fi

# Verify that required packages are installed
if ! python -c "import flask" 2>/dev/null; then
  echo "Flask is not installed in the current environment."
  echo "Installing required packages..."
  pip install flask flask-cors pydantic typer rich psutil
fi

# Kill any existing processes on ports 8000 and 8001
echo "Checking for processes using ports 8000 and 8001..."
if command_exists lsof; then
  API_PIDS=$(lsof -ti:8000)
  GUI_PIDS=$(lsof -ti:8001)
  
  if [ ! -z "$API_PIDS" ]; then
    echo "Stopping processes using port 8000: $API_PIDS"
    kill -9 $API_PIDS 2>/dev/null
  fi
  
  if [ ! -z "$GUI_PIDS" ]; then
    echo "Stopping processes using port 8001: $GUI_PIDS"
    kill -9 $GUI_PIDS 2>/dev/null
  fi
fi

# Wait a moment for processes to terminate
sleep 1

# Start API server directly
echo "Starting API server on port 8000..."
FLASK_APP=api_server.py python api_server.py --port 8000 &
API_PID=$!

# Wait for API to start
sleep 2

# Start GUI server directly
echo "Starting GUI server on port 8001..."
FLASK_APP=gui_server.py python gui_server.py --port 8001 --api-url http://localhost:8000 &
GUI_PID=$!

echo ""
echo "Servers started with direct execution:"
echo "  - API server: http://localhost:8000 (PID: $API_PID)"
echo "  - GUI server: http://localhost:8001 (PID: $GUI_PID)"
echo ""
echo "You can access the web interface by opening: http://localhost:8001"
echo "To stop the servers, press Ctrl+C or run: kill -9 $API_PID $GUI_PID"
echo ""

# Wait for user to press Ctrl+C
trap "kill $API_PID $GUI_PID 2>/dev/null; echo 'Servers stopped.'; exit 0" INT
wait