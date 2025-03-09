#!/bin/bash
# Script to diagnose and fix CLI environment issues

echo "===== Carchive CLI Environment Diagnostic Tool ====="
echo ""

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check Python version
echo "Python version:"
python --version

# Check pip installation
echo ""
echo "Pip version:"
pip --version

# Check virtual environments
echo ""
echo "Checking for virtual environments:"
if [ -d "mac_venv" ]; then
  echo "✓ mac_venv directory exists"
else
  echo "✗ mac_venv directory not found"
fi

if [ -d "venv" ]; then
  echo "✓ venv directory exists"
else
  echo "✗ venv directory not found"
fi

if [ -d "venv_310" ]; then
  echo "✓ venv_310 directory exists"
else
  echo "✗ venv_310 directory not found"
fi

# Check if conda is available
if command_exists conda; then
  echo "✓ conda is available"
  echo ""
  echo "Conda environments:"
  conda env list
else
  echo "✗ conda is not available"
fi

# Check for poetry
echo ""
if command_exists poetry; then
  echo "✓ Poetry is installed"
  POETRY_VERSION=$(poetry --version)
  echo "  $POETRY_VERSION"
else
  echo "✗ Poetry is not installed"
fi

# Check installed packages
echo ""
echo "Checking for required packages in current environment:"
PACKAGES=("flask" "flask-cors" "pydantic" "typer" "sqlalchemy" "psycopg2" "psutil")

for pkg in "${PACKAGES[@]}"; do
  if python -c "import ${pkg//-/_}" 2>/dev/null; then
    echo "✓ $pkg is installed"
  else
    echo "✗ $pkg is not installed"
  fi
done

# Check if carchive is installed in development mode
echo ""
echo "Checking if carchive is installed in development mode:"
if python -c "import carchive" 2>/dev/null; then
  echo "✓ carchive package is importable"
  
  # Try to get version or location
  if python -c "import carchive; print(carchive.__file__)" 2>/dev/null; then
    CARCHIVE_PATH=$(python -c "import carchive; print(carchive.__file__)")
    echo "  Location: $CARCHIVE_PATH"
    
    if [[ "$CARCHIVE_PATH" == *"/src/carchive/__init__.py"* ]]; then
      echo "  ✓ Installed in development mode"
    else
      echo "  ✗ Not installed in development mode"
    fi
  fi
else
  echo "✗ carchive package is not importable"
fi

# Fix environment
echo ""
echo "Would you like to fix the environment issues? (y/n)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
  echo ""
  echo "===== Fixing Environment ====="
  
  # Activate appropriate environment
  if [ -d "mac_venv" ]; then
    echo "Activating mac_venv..."
    source mac_venv/bin/activate
  elif [ -d "venv" ]; then
    echo "Activating venv..."
    source venv/bin/activate
  elif [ -d "venv_310" ]; then
    echo "Activating venv_310..."
    source venv_310/bin/activate
  elif command_exists conda; then
    echo "Activating conda environment..."
    conda activate carchive-py3.10 2>/dev/null || conda activate base
  fi
  
  # Install required packages
  echo "Installing required packages..."
  pip install flask flask-cors pydantic typer rich psutil sqlalchemy psycopg2-binary
  
  # Install carchive in development mode
  echo "Installing carchive in development mode..."
  pip install -e .
  
  echo ""
  echo "Environment setup complete. Try running the carchive CLI again."
  echo "Example: carchive server status"
  
  # Create an activation script for the user
  cat > activate_carchive.sh << 'EOL'
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
EOL
  
  chmod +x activate_carchive.sh
  echo ""
  echo "Created activation script. Use it with: source activate_carchive.sh"
fi