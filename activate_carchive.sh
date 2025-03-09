#!/bin/bash
# Source this file to activate the carchive environment
# Usage: source activate_carchive.sh

if [ -d "mac_venv" ]; then
  source mac_venv/bin/activate
  echo "Activated mac_venv environment"
elif [ -d "venv" ]; then
  source venv/bin/activate
  echo "Activated venv environment"
elif [ -d "venv_310" ]; then
  source venv_310/bin/activate
  echo "Activated venv_310 environment"
elif command -v conda >/dev/null 2>&1; then
  conda activate carchive-py3.10 2>/dev/null || conda activate base
  echo "Activated conda environment"
else
  echo "No suitable environment found"
  return 1
fi

# Set environment variables
export FLASK_APP=api_server.py
export CARCHIVE_DEBUG=1

echo "Carchive environment activated. You can now run carchive commands."
