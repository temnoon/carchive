#!/bin/bash
# Run the API server with the recovery environment
source ./venv_recovery/bin/activate
echo "Starting API server with recovery environment..."
python api_server.py $@
