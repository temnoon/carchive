#!/bin/bash

# Create a clean carchive2 environment using the anaconda3 installation
echo "Setting up carchive2 environment..."

# Use the full anaconda path
CONDA_PATH="/Users/tem/anaconda3/bin/conda"

# Create environment
echo "Creating conda environment carchive2_env..."
$CONDA_PATH create -n carchive2_env python=3.10 -y

# Install dependencies
echo "Installing dependencies..."
$CONDA_PATH run -n carchive2_env pip install -r requirements.txt

# Install package in development mode
echo "Installing carchive2 in development mode..."
$CONDA_PATH run -n carchive2_env pip install -e .

echo "Environment setup complete!"
echo "To activate, run: /Users/tem/anaconda3/bin/conda activate carchive2_env"