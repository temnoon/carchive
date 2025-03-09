#!/bin/bash
# Script to recover the carchive environment with minimal changes

echo "Starting recovery of carchive environment..."

# 1. Create a new virtual environment with Python 3.10
VENV_PATH="./venv_recovery"
echo "Creating virtual environment at $VENV_PATH using Python 3.10..."
python3.10 -m venv $VENV_PATH

# 2. Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# 3. Install poetry
echo "Installing poetry..."
pip install poetry

# 4. Update the lock file safely
echo "Updating poetry lock file to match current dependencies..."
cd /Users/tem/archive/carchive
poetry lock --no-update # This will only update the lock file format without changing deps

# 5. Install deps from the lock file
echo "Installing dependencies from lock file..."
poetry install

# 6. Test if the CLI works
echo "Testing the CLI..."
poetry run carchive --help

# 7. Create run scripts
echo "Creating run scripts for recovery environment..."

# API server script
cat > run_api_recovery.sh << EOF
#!/bin/bash
# Run the API server with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting API server with recovery environment..."
python api_server.py \$@
EOF

# GUI server script
cat > run_gui_recovery.sh << EOF
#!/bin/bash
# Run the GUI server with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting GUI server with recovery environment..."
python gui_server.py \$@
EOF

# CLI helper script
cat > run_cli_recovery.sh << EOF
#!/bin/bash
# Run the CLI with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting carchive CLI with recovery environment..."
poetry run carchive "\$@"
EOF

# Make scripts executable
chmod +x run_api_recovery.sh run_gui_recovery.sh run_cli_recovery.sh

echo "Recovery complete!"
echo "To run the CLI: ./run_cli_recovery.sh [command]"
echo "To run the API server: ./run_api_recovery.sh"
echo "To run the GUI server: ./run_gui_recovery.sh"