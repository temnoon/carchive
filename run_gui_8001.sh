#!/bin/bash
# GUI server on port 8001

# Activate the Python environment (prefer mac_venv if available)
if [ -d "mac_venv" ]; then
    source mac_venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Flask environment
export FLASK_APP=gui_server.py
export FLASK_DEBUG=0

# Set API URL to connect to
export CARCHIVE_API_URL="http://localhost:8000"

# Run the server
echo "Starting GUI server on port 8001..."
echo "Connected to API at $CARCHIVE_API_URL"
python gui_server.py --port 8001 --api-url $CARCHIVE_API_URL "$@"