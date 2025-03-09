#!/bin/bash
# Improved script to recover the carchive environment

echo "Starting recovery of carchive environment (version 2)..."

# 1. Create a new virtual environment with Python 3.10
VENV_PATH="./venv_recovery2"
echo "Creating virtual environment at $VENV_PATH using Python 3.10..."
python3.10 -m venv $VENV_PATH

# 2. Activate the environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# 3. Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# 4. Install poetry
echo "Installing poetry..."
pip install poetry

# 5. First install core dependencies directly with pip
echo "Installing core dependencies directly with pip..."
pip install typer flask flask-cors uvicorn sqlalchemy psycopg2-binary pydantic==1.10.21

# 6. Generate a fresh lock file
echo "Regenerating poetry lock file from scratch..."
cd /Users/tem/archive/carchive
poetry lock

# 7. Install all dependencies
echo "Installing all dependencies from the updated lock file..."
poetry install

# 8. Test if the CLI works
echo "Testing the CLI..."
poetry run carchive --help

# 9. Create run scripts
echo "Creating run scripts for recovery environment..."

# API server script
cat > run_api_recovery2.sh << EOF
#!/bin/bash
# Run the API server with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting API server with recovery environment..."
cd /Users/tem/archive/carchive
python api_server.py \$@
EOF

# GUI server script
cat > run_gui_recovery2.sh << EOF
#!/bin/bash
# Run the GUI server with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting GUI server with recovery environment..."
cd /Users/tem/archive/carchive
python gui_server.py \$@
EOF

# CLI helper script
cat > run_cli_recovery2.sh << EOF
#!/bin/bash
# Run the CLI with the recovery environment
source $VENV_PATH/bin/activate
echo "Starting carchive CLI with recovery environment..."
cd /Users/tem/archive/carchive
poetry run carchive "\$@"
EOF

# Make scripts executable
chmod +x run_api_recovery2.sh run_gui_recovery2.sh run_cli_recovery2.sh

echo "Recovery v2 complete!"
echo "To run the CLI: ./run_cli_recovery2.sh [command]"
echo "To run the API server: ./run_api_recovery2.sh"
echo "To run the GUI server: ./run_gui_recovery2.sh"