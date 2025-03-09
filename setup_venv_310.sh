#!/bin/bash

# Create a Python 3.10 virtual environment for carchive
# This bypasses the issues with Python 3.13

echo "Setting up Python 3.10 virtual environment for carchive..."

# Define the environment path
VENV_PATH="./venv_310"

# Create a virtual environment with Python 3.10
echo "Creating virtual environment at $VENV_PATH using Python 3.10..."
python3.10 -m venv $VENV_PATH

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install poetry inside the virtual environment
echo "Installing poetry in the virtual environment..."
pip install poetry

# Use poetry to install dependencies
echo "Installing dependencies via poetry..."
poetry install

# Create run scripts for the Python 3.10 environment
echo "Creating run scripts..."

# Create API server script
cat > run_api_py310.sh << EOF
#!/bin/bash
# Run the API server using the Python 3.10 environment
source $VENV_PATH/bin/activate
echo "Starting API server with Python 3.10..."
python api_server.py \$@
EOF

# Create GUI server script
cat > run_gui_py310.sh << EOF
#!/bin/bash
# Run the GUI server using the Python 3.10 environment
source $VENV_PATH/bin/activate
echo "Starting GUI server with Python 3.10..."
python gui_server.py \$@
EOF

# Make scripts executable
chmod +x run_api_py310.sh run_gui_py310.sh

echo "Python 3.10 setup complete!"
echo "To run the API server: ./run_api_py310.sh"
echo "To run the GUI server: ./run_gui_py310.sh"