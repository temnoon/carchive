#!/bin/bash

# Quick script to install missing pymdown-extensions package

echo "Installing missing Markdown extensions..."

# Define the environment path
VENV_PATH="./mac_venv"

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Install the pymdown-extensions package
echo "Installing pymdown-extensions..."
pip install pymdown-extensions

echo "Installation complete!"
echo "You can now run the servers with:"
echo "  ./run_api_fixed.sh"
echo "  ./run_gui_fixed.sh"