#!/bin/bash
# Script to create a clean Python 3.10 environment for carchive

echo "Creating a new Python 3.10 environment for carchive..."

# Check if Python 3.10 is installed
if ! command -v python3.10 >/dev/null 2>&1; then
  echo "Python 3.10 is not installed. Please install it first."
  echo "For macOS, you can use:"
  echo "  brew install python@3.10"
  exit 1
fi

# Create a new venv using Python 3.10
echo "Creating virtual environment in venv_310 directory..."
python3.10 -m venv venv_310

# Activate the new environment
source venv_310/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install the package in development mode
echo "Installing carchive in development mode..."
pip install -e .

echo ""
echo "Python 3.10 environment created successfully!"
echo "To activate this environment, use:"
echo "  source venv_310/bin/activate"
echo ""
echo "Or use the provided activation script:"
echo "  source activate.sh"