#!/bin/bash
# Script to install missing dependencies for the carchive project in recovery environment

echo "Installing missing dependencies for recovery environment..."

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Install additional required packages
pip install fastapi
pip install pgvector
pip install scikit-learn
pip install matplotlib
pip install pymdown-extensions
pip install tqdm
pip install weasyprint
pip install pylatexenc
pip install groq
pip install psutil
pip install jinja2==3.1.2  # Specific version to avoid compatibility issues

# Check installation status
echo "Checking installation..."
pip list | grep -E 'fastapi|flask|uvicorn'

echo "Dependencies installed. Try running the servers again."