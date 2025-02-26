#!/bin/bash

# Create a Python virtual environment for carchive2 without using conda
# This bypasses any conda issues

echo "Setting up Python virtual environment for carchive2..."

# Define the environment path
VENV_PATH="./venv"

# Create a virtual environment
echo "Creating virtual environment at $VENV_PATH..."
python3 -m venv $VENV_PATH

# Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install the package in development mode
echo "Installing carchive2 in development mode..."
pip install -e .

# Create run scripts for the venv
echo "Creating run scripts..."

# Create API server script
cat > run_api_venv.sh << EOF
#!/bin/bash
# Run the API server using the Python virtual environment
source $VENV_PATH/bin/activate
echo "Starting API server..."
python api_server.py \$@
EOF

# Create GUI server script
cat > run_gui_venv.sh << EOF
#!/bin/bash
# Run the GUI server using the Python virtual environment
source $VENV_PATH/bin/activate
echo "Starting GUI server..."
python gui_server.py \$@
EOF

# Make scripts executable
chmod +x run_api_venv.sh run_gui_venv.sh

echo "Setup complete!"
echo "To run the API server: ./run_api_venv.sh"
echo "To run the GUI server: ./run_gui_venv.sh"

# Deactivate the virtual environment
deactivate