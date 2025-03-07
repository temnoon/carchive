#!/bin/bash
# Run the API server on port 8000 with the recovery environment
# This script is part of the standardization to ports 8000/8001

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Run API server on port 8000
echo "Starting API server on port 8000..."
python api_server.py --port 8000 "$@"