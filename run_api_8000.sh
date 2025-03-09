#!/bin/bash
# API server on port 8000

# Activate the Python environment (prefer mac_venv if available)
if [ -d "mac_venv" ]; then
    source mac_venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set Flask environment
export FLASK_APP=api_server.py
export FLASK_DEBUG=0

# Set database connection (if needed)
# export CARCHIVE_DB_URI="postgresql://carchive_app:carchive_pass@localhost:5432/carchive04_db"

# Set other environment variables
export CARCHIVE_CORS_ENABLED=1

# Run the server
echo "Starting API server on port 8000..."
python api_server.py --port 8000 "$@"