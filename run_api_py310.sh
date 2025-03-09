#!/bin/bash
# Run the API server using the Python 3.10 environment
source ./venv_310/bin/activate
echo "Starting API server with Python 3.10..."
python api_server.py $@
