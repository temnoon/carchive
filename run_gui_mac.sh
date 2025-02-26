#!/bin/bash
# Run the GUI server using the Mac-optimized environment
source ./mac_venv/bin/activate
echo "Starting GUI server with Mac optimizations..."
python gui_server.py $@
