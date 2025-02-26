#!/bin/bash
# Run the API server using the Python virtual environment
source ./venv/bin/activate
echo "Starting API server..."
python api_server.py $@
