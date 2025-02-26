#!/bin/bash

# Script to set up the carchive2 development environment
set -e  # Exit on error

# Environment name
ENV_NAME="carchive2_env"

# Create a fresh conda environment
echo "Creating fresh conda environment: $ENV_NAME"
conda create -n $ENV_NAME python=3.10 -y

# Activate the environment
echo "Activating conda environment"
eval "$(conda shell.bash hook)"
conda activate $ENV_NAME

# Install dependencies from requirements.txt
echo "Installing dependencies from requirements.txt"
conda install -y --file requirements.txt

# Install the package in development mode
echo "Installing carchive2 in development mode"
pip install -e .

echo "Environment setup complete! You can now activate it with:"
echo "conda activate $ENV_NAME"