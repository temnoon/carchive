#!/bin/bash
# Run the API server using the Mac-optimized environment
source ./mac_venv/bin/activate
echo "Starting API server with Mac optimizations..."
python api_server.py $@
