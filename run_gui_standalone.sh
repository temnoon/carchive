#!/bin/bash
# Run the GUI server with minimal configuration
source ./mac_venv/bin/activate
export FLASK_ENV=development
export FLASK_DEBUG=1
export FLASK_APP=carchive2.gui
echo "Starting GUI server in standalone mode..."

# Run directly with flask
flask run --host=127.0.0.1 --port=5001