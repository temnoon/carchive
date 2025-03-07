#!/bin/bash
# Script to start both API and GUI servers with the recovery environment
# Using ports 8000 (API) and 8001 (GUI)

echo "Restarting API and GUI servers with ports 8000 and 8001..."

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# More reliable process termination function
kill_port_processes() {
    local PORT=$1
    local PIDS=$(lsof -ti:$PORT)
    
    if [ ! -z "$PIDS" ]; then
        echo "Stopping processes on port $PORT (PIDs: $PIDS)..."
        echo $PIDS | xargs kill -9
        sleep 1
    else
        echo "No processes found on port $PORT"
    fi
}

# Stop any existing servers on these ports
kill_port_processes 8000
kill_port_processes 8001

# Wait to ensure ports are cleared
sleep 2

# Check if embeddings.py has a correct import
if grep -q "from carchive.database.session import db_session$" src/carchive/api/routes/embeddings.py; then
    # Fix the import in embeddings.py
    echo "Fixing import in embeddings.py..."
    sed -i '' 's/from carchive.database.session import db_session$/from carchive.database.session import db_session, get_session/' src/carchive/api/routes/embeddings.py
fi

# Start the API server
echo "Starting API server on port 8000..."
python api_server.py --host 127.0.0.1 --port 8000 &
API_PID=$!

# Wait a moment for the API server to start
sleep 3

# Check if API server started successfully
if ! ps -p $API_PID > /dev/null; then
    echo "ERROR: API server failed to start. Check logs above for errors."
    exit 1
fi

echo "API server running with PID: $API_PID"

# Start the GUI server
echo "Starting GUI server on port 8001..."
python gui_server.py --host 127.0.0.1 --port 8001 --api-url http://127.0.0.1:8000 &
GUI_PID=$!

# Wait to see if GUI started successfully
sleep 3

# Check if GUI server started successfully
if ! ps -p $GUI_PID > /dev/null; then
    echo "ERROR: GUI server failed to start. Check logs above for errors."
    echo "Stopping API server..."
    kill $API_PID
    exit 1
fi

echo "GUI server running with PID: $GUI_PID"
echo ""
echo "Servers started successfully!"
echo "API server running at http://127.0.0.1:8000"
echo "GUI server running at http://127.0.0.1:8001"
echo ""
echo "You can access the web interface by opening http://127.0.0.1:8001 in your browser."
echo ""
echo "To stop the servers, run: kill $API_PID $GUI_PID"
echo "Or use: kill_port_processes 8000; kill_port_processes 8001"