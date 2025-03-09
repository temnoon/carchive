#!/bin/bash
# Run the API server with the recovery environment
source ./venv_recovery2/bin/activate
echo "Starting API server with recovery environment..."
cd /Users/tem/archive/carchive
python api_server.py $@
