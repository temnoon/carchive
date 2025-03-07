#!/bin/bash
# Run the API server on port 8000 with the recovery environment
source ./venv_recovery2/bin/activate
echo "Starting API server on port 8000 with recovery environment..."
python api_server.py --host 127.0.0.1 --port 8000