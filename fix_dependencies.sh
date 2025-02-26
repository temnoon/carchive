#!/bin/bash

# Script to fix the dependency issues by directly installing
# only the necessary packages without version conflicts

echo "Fixing dependency issues..."

# Define the environment path
VENV_PATH="./mac_venv"

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Install the core requirements explicitly
echo "Installing core dependencies..."
pip install pydantic==1.10.21 requests rich

# Install remaining packages without dependency conflicts
echo "Installing remaining dependencies..."
pip install flask==2.2.5 flask-cors uvicorn==0.17.6 
pip install sqlalchemy psycopg2 pgvector 
pip install typer click markdown python-dotenv keyring greenlet
pip install jinja2

echo "All dependencies installed!"
echo "You can now run the servers with:"
echo "  ./run_api_mac.sh"
echo "  ./run_gui_mac.sh"