#!/bin/bash
# Unified environment setup script using the new CLI commands
# This replaces the various setup_*.sh and fix_*.sh scripts

# Detect OS and machine type
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Detected macOS"
    IS_MAC=true
    
    # Check for Apple Silicon
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Detected Apple Silicon (M1/M2/M3)"
        IS_APPLE_SILICON=true
    else
        echo "Detected Intel Mac"
        IS_APPLE_SILICON=false
    fi
else
    echo "Detected non-macOS system"
    IS_MAC=false
    IS_APPLE_SILICON=false
fi

# Recommend environment type based on detected platform
if [[ "$IS_APPLE_SILICON" == true ]]; then
    DEFAULT_ENV_TYPE="mac-optimized"
    DEFAULT_PATH="./mac_venv"
elif [[ "$IS_MAC" == true ]]; then
    DEFAULT_ENV_TYPE="standard"
    DEFAULT_PATH="./venv"
else
    DEFAULT_ENV_TYPE="standard"
    DEFAULT_PATH="./venv"
fi

# Ask user for environment type
echo ""
echo "Recommended environment type for your system: $DEFAULT_ENV_TYPE"
read -p "Environment type (standard, mac-optimized, minimal) [$DEFAULT_ENV_TYPE]: " ENV_TYPE
ENV_TYPE=${ENV_TYPE:-$DEFAULT_ENV_TYPE}

# Ask user for environment path
read -p "Environment path [$DEFAULT_PATH]: " ENV_PATH
ENV_PATH=${ENV_PATH:-$DEFAULT_PATH}

# Ask user if they want to force recreation
read -p "Force recreation of existing environment? (y/n) [n]: " FORCE_RECREATE
FORCE_RECREATE=${FORCE_RECREATE:-n}

FORCE_FLAG=""
if [[ "$FORCE_RECREATE" =~ ^[Yy]$ ]]; then
    FORCE_FLAG="--force"
fi

# Create the environment
echo ""
echo "Setting up $ENV_TYPE environment at $ENV_PATH..."
if ! python3 -m pip install poetry >/dev/null 2>&1; then
    echo "Installing poetry..."
    python3 -m pip install poetry
fi

python3 -m poetry run carchive env setup --env-type="$ENV_TYPE" --path="$ENV_PATH" $FORCE_FLAG

# Check for issues
echo ""
echo "Checking for environment issues..."
python3 -m poetry run carchive env check

# Ask user if they want to fix CORS
echo ""
read -p "Fix CORS settings for API and GUI servers? (y/n) [y]: " FIX_CORS
FIX_CORS=${FIX_CORS:-y}

if [[ "$FIX_CORS" =~ ^[Yy]$ ]]; then
    python3 -m poetry run carchive env fix-cors
fi

# Check database
echo ""
read -p "Check database configuration? (y/n) [y]: " CHECK_DB
CHECK_DB=${CHECK_DB:-y}

if [[ "$CHECK_DB" =~ ^[Yy]$ ]]; then
    python3 -m poetry run carchive db validate
fi

echo ""
echo "Environment setup complete!"
echo "To run the API server: ./run_api_${ENV_TYPE//-/_}.sh"
echo "To run the GUI server: ./run_gui_${ENV_TYPE//-/_}.sh"