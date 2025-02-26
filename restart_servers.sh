#!/bin/bash

# This script restarts both API and GUI servers with all templates loaded

echo "Restarting API and GUI servers..."

# Kill any processes using ports 5000 and 5001
echo "Stopping any processes using ports 5000 and 5001..."

# Check for processes using port 5000 (API)
API_PIDS=$(lsof -ti:5000)
if [ ! -z "$API_PIDS" ]; then
    echo "Killing processes using port 5000: $API_PIDS"
    kill -9 $API_PIDS 2>/dev/null || true
fi

# Check for processes using port 5001 (GUI)
GUI_PIDS=$(lsof -ti:5001)
if [ ! -z "$GUI_PIDS" ]; then
    echo "Killing processes using port 5001: $GUI_PIDS"
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

# Start the servers with enhanced CORS
echo "Starting API server with enhanced CORS..."
./run_api_with_cors.sh &
API_PID=$!

# Wait a moment for the API server to start
sleep 2

echo "Starting GUI server..."
./run_gui_with_cors.sh &
GUI_PID=$!

echo "Servers restarted!"
echo "API server running at http://127.0.0.1:5000"
echo "GUI server running at http://127.0.0.1:5001"
echo ""
echo "You can access the web interface by opening http://127.0.0.1:5001 in your browser."
echo "All templates have been created and should now load properly."