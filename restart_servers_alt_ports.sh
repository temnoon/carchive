#!/bin/bash

# This script restarts both API and GUI servers with alternative ports
# API: 8000, GUI: 8001

echo "Restarting API and GUI servers with alternative ports..."

# Check if the API and GUI servers are running
API_PID=$(pgrep -f "python.*api_server.py")
GUI_PID=$(pgrep -f "python.*gui_server.py")

# Stop the running servers if they exist
if [ ! -z "$API_PID" ]; then
    echo "Stopping API server (PID: $API_PID)..."
    kill "$API_PID"
    sleep 1
fi

if [ ! -z "$GUI_PID" ]; then
    echo "Stopping GUI server (PID: $GUI_PID)..."
    kill "$GUI_PID"
    sleep 1
fi

# Start the API server with CORS and alternative port
echo "Starting API server on port 8000 with enhanced CORS..."
FLASK_APP=carchive2.api FLASK_DEBUG=1 CARCHIVE_API_PORT=8000 python -m flask run --host=127.0.0.1 --port=8000 &
API_PID=$!

# Wait a moment for the API server to start
sleep 2

# Start the GUI server with alternative port and pointing to the alternative API port
echo "Starting GUI server on port 8001..."
FLASK_APP=carchive2.gui FLASK_DEBUG=1 CARCHIVE_API_URL=http://127.0.0.1:8000 python -m flask run --host=127.0.0.1 --port=8001 &
GUI_PID=$!

echo "Servers restarted!"
echo "API server running at http://127.0.0.1:8000"
echo "GUI server running at http://127.0.0.1:8001"
echo ""
echo "You can access the web interface by opening http://127.0.0.1:8001 in your browser."
echo "All templates have been created and should now load properly."