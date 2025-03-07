#!/bin/bash
# Run the GUI server on port 8001 with the recovery environment
source ./venv_recovery2/bin/activate
echo "Starting GUI server on port 8001 with recovery environment..."
python gui_server.py --host 127.0.0.1 --port 8001 --api-url http://127.0.0.1:8000