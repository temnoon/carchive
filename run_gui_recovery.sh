#!/bin/bash
# Run the GUI server with the recovery environment
source ./venv_recovery/bin/activate
echo "Starting GUI server with recovery environment..."
python gui_server.py $@
