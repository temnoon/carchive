#!/bin/bash
# Run the GUI server with the recovery environment
source ./venv_recovery2/bin/activate
echo "Starting GUI server with recovery environment..."
cd /Users/tem/archive/carchive
python gui_server.py $@
