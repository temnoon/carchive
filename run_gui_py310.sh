#!/bin/bash
# Run the GUI server using the Python 3.10 environment
source ./venv_310/bin/activate
echo "Starting GUI server with Python 3.10..."
python gui_server.py $@
