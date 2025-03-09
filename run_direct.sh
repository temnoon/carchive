#!/bin/bash
# Direct server launcher that bypasses the CLI
# Only use this if the regular CLI is not working

# Ensure Python 3.10 environment is activated
if [ -d "venv_310" ]; then
  source venv_310/bin/activate
  echo "Using Python 3.10 environment"
else
  echo "Error: Python 3.10 environment not found"
  echo "Please run: ./create_py310_env.sh"
  exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="$PWD/src:$PYTHONPATH"

# Check for required packages and install if missing
for pkg in flask flask_cors rich typer; do
  if ! python -c "import $pkg" 2>/dev/null; then
    echo "Installing $pkg..."
    pip install $pkg
  fi
done

echo "Starting API server on port 8000..."

# Run API server directly
python -c "
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from flask import Flask
from carchive.api.app import create_api_app

app = create_api_app()
app.run(host='127.0.0.1', port=8000, debug=False)
" &

API_PID=$!

sleep 2

echo "Starting GUI server on port 8001..."

# Run GUI server directly
python -c "
import os
import sys
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from flask import Flask
from carchive.gui import create_app

app = create_app({
    'API_URL': 'http://127.0.0.1:8000',
    'DEBUG': False
})
app.run(host='127.0.0.1', port=8001, debug=False)
" &

GUI_PID=$!

echo ""
echo "Servers started:"
echo "  - API server: http://127.0.0.1:8000 (PID: $API_PID)"
echo "  - GUI server: http://127.0.0.1:8001 (PID: $GUI_PID)"
echo ""
echo "To access the web interface, open: http://127.0.0.1:8001"
echo "To stop the servers, press Ctrl+C or run: kill -9 $API_PID $GUI_PID"

# Wait for Ctrl+C
trap "kill $API_PID $GUI_PID 2>/dev/null; echo 'Servers stopped.'; exit 0" INT
wait