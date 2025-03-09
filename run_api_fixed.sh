#!/bin/bash
# Run the API server with the recovery environment and all fixes applied

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Run API server
echo "Starting API server with recovery environment..."
python api_server.py "$@"
