#!/bin/bash

# Script to run the carchive2 GUI server
# Activates the conda environment and runs the GUI server

# Environment name
ENV_NAME="carchive2_env"

# Use full path to conda
CONDA_PATH="/Users/tem/anaconda3/bin/conda"

# Activate the environment
echo "Activating conda environment: $ENV_NAME"
source /Users/tem/anaconda3/bin/activate $ENV_NAME

# Run the GUI server
echo "Starting GUI server..."
python gui_server.py "$@"