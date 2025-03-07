#!/bin/bash
# Run the GUI server on port 8001 with the recovery environment
# This script is part of the standardization to ports 8000/8001

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Run GUI server on port 8001 connecting to API at port 8000
echo "Starting GUI server on port 8001..."
python gui_server.py --port 8001 --api-url http://localhost:8000 "$@"