#!/bin/bash
# Run the GUI server
source ./mac_venv/bin/activate
echo "Starting GUI server..."
python gui_server.py $@
