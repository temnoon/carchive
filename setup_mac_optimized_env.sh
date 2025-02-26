#!/bin/bash

# Create a Mac-optimized Python environment for carchive2
# Incorporates optimizations for Apple Silicon and unified memory

echo "Setting up Mac-optimized Python environment for carchive2..."

# Define the environment path
VENV_PATH="./mac_venv"

# Check if running on Apple Silicon
if [[ $(uname -m) == "arm64" ]]; then
    echo "Detected Apple Silicon (M1/M2/M3)"
    IS_APPLE_SILICON=true
else
    echo "Detected Intel Mac"
    IS_APPLE_SILICON=false
fi

# Create a virtual environment
echo "Creating virtual environment at $VENV_PATH..."
python3 -m venv $VENV_PATH

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Set Mac-specific optimization flags
if [[ "$IS_APPLE_SILICON" == true ]]; then
    echo "Setting Apple Silicon optimization flags..."
    export TCMALLOC_LARGE_ALLOC_REPORT_THRESHOLD=10000000000
    export PYTORCH_ENABLE_MPS_FALLBACK=1

    # Create environment configuration file with Mac optimizations
    mkdir -p $VENV_PATH/etc
    cat > $VENV_PATH/etc/mac_optimizations.sh << EOF
# Mac-specific optimizations for Python environment
# Especially for Apple Silicon (M1/M2/M3)

# Memory optimizations for unified memory
export TCMALLOC_LARGE_ALLOC_REPORT_THRESHOLD=10000000000

# PyTorch MPS (Metal Performance Shaders) support
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Accelerate NumPy with Metal
export ACCELERATE_USE_SYSTEM=true

# OpenMP thread optimizations
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8

# PostgreSQL optimizations
export PSYCOPG_IMPL=c
EOF

    # Source the optimizations in the activation script
    echo "source \"\$VIRTUAL_ENV/etc/mac_optimizations.sh\"" >> $VENV_PATH/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies with Mac-specific optimizations
echo "Installing dependencies with Mac optimizations..."
if [[ "$IS_APPLE_SILICON" == true ]]; then
    # Use wheels optimized for Apple Silicon where available
    PIP_EXTRA_INDEX_URL="https://pypi.anaconda.org/scipy-wheels-nightly/simple"
    CFLAGS="-I/opt/homebrew/include -O3 -march=native" LDFLAGS="-L/opt/homebrew/lib" pip install -r requirements.txt
else
    # Regular installation for Intel Macs
    pip install -r requirements.txt
fi

# Install the package in development mode
echo "Installing carchive2 in development mode..."
pip install -e .

# Create run scripts for the mac-optimized environment
echo "Creating run scripts..."

# Create API server script
cat > run_api_mac.sh << EOF
#!/bin/bash
# Run the API server using the Mac-optimized environment
source $VENV_PATH/bin/activate
echo "Starting API server with Mac optimizations..."
python api_server.py \$@
EOF

# Create GUI server script
cat > run_gui_mac.sh << EOF
#!/bin/bash
# Run the GUI server using the Mac-optimized environment
source $VENV_PATH/bin/activate
echo "Starting GUI server with Mac optimizations..."
python gui_server.py \$@
EOF

# Make scripts executable
chmod +x run_api_mac.sh run_gui_mac.sh

echo "Mac-optimized setup complete!"
echo "To run the API server: ./run_api_mac.sh"
echo "To run the GUI server: ./run_gui_mac.sh"

# Deactivate the virtual environment
deactivate