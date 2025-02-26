#!/bin/bash
# Run the API server
source ./mac_venv/bin/activate
echo "Starting API server..."
python api_server.py $@
