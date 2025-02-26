#!/bin/bash

# Script to install missing dependencies in the Mac environment

echo "Installing missing dependencies..."

# Define the environment path
VENV_PATH="./mac_venv"

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Install the requests package
echo "Installing requests package..."
pip install requests

# Install any other missing packages from requirements.txt
echo "Installing any other missing dependencies..."
pip install -r requirements.txt

echo "All dependencies installed!"
echo "You can now run the servers with:"
echo "  ./run_api_mac.sh"
echo "  ./run_gui_mac.sh"

# Deactivate the environment
deactivate