#!/bin/bash
# Run the GUI server using the Python virtual environment
source ./venv/bin/activate
echo "Starting GUI server..."
python gui_server.py $@
