#!/bin/bash
# Combined script to run both API and GUI servers on standardized ports

# This script starts both the API server on port 8000 and the GUI server on port 8001

# First, check if ports are already in use
API_PORT=8000
GUI_PORT=8001

check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check if ports are in use and kill processes if needed
if check_port $API_PORT; then
    echo "Port $API_PORT is already in use. Attempting to free it..."
    lsof -ti:$API_PORT | xargs kill -9
    sleep 1
fi

if check_port $GUI_PORT; then
    echo "Port $GUI_PORT is already in use. Attempting to free it..."
    lsof -ti:$GUI_PORT | xargs kill -9
    sleep 1
fi

# Activate the Python environment (prefer mac_venv if available)
if [ -d "mac_venv" ]; then
    source mac_venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start API server
echo "Starting API server on port $API_PORT..."
./run_api_8000.sh &
API_PID=$!

# Wait a moment for the API server to start
sleep 2

# Start GUI server
echo "Starting GUI server on port $GUI_PORT..."
./run_gui_8001.sh &
GUI_PID=$!

echo ""
echo "Both servers have been started:"
echo "  - API server: http://localhost:$API_PORT (PID: $API_PID)"
echo "  - GUI server: http://localhost:$GUI_PORT (PID: $GUI_PID)"
echo ""
echo "You can access the web interface by opening: http://localhost:$GUI_PORT"
echo "To stop the servers, press Ctrl+C or run: ./run_servers.sh stop"
echo ""

# Make the script wait (otherwise it will exit and kill the background processes)
wait