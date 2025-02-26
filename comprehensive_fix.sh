#!/bin/bash

# A comprehensive script to fix the environment and start the servers
# This handles potential dependency conflicts and installs all necessary packages

# Set -e to exit on error
set -e

echo "Starting comprehensive environment fix..."

# Define the environment path
VENV_PATH="./mac_venv"

# Check if venv exists and activate it
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating new virtual environment at $VENV_PATH..."
    python3 -m venv $VENV_PATH
fi

# Activate environment
echo "Activating virtual environment..."
source $VENV_PATH/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install base dependencies first (no constraints)
echo "Installing base dependencies..."
pip install wheel

# Install core requirements in the correct order to avoid conflicts
echo "Installing core dependencies in correct order..."
pip install pydantic==1.10.21
pip install requests
pip install rich
pip install flask==2.2.5 werkzeug
pip install flask-cors
pip install sqlalchemy
pip install greenlet
pip install psycopg2
pip install pgvector
pip install typer click
pip install markdown
pip install python-dotenv
pip install keyring
pip install asgiref h11
pip install uvicorn==0.17.6

# Install markdown extensions
echo "Installing Markdown extensions..."
pip install pymdown-extensions

# Install the carchive2 package in development mode
echo "Installing carchive2 in development mode..."
pip install -e .

# Check if we need a .env file and create if missing
if [ ! -f .env ]; then
    echo "Creating basic .env file..."
    cat > .env << EOF
# Database connection settings
# DB_USER=carchive_app
# DB_PASSWORD=your_password_here
# DB_HOST=localhost
# DB_NAME=carchive03_db

# External API settings
# OPENAI_API_KEY=your_openai_key_here
# ANTHROPIC_API_KEY=your_anthropic_key_here
OLLAMA_URL=http://localhost:11434

# Embedding settings
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL_NAME=nomic-embed-text
EMBEDDING_DIMENSIONS=768

# Model settings
VISION_MODEL_NAME=llama3.2-vision
TEXT_MODEL_NAME=llama3.2
EOF
    echo ".env file created with default settings"
fi

# Create run scripts for API and GUI
echo "Creating convenient run scripts..."

# Create API server script
cat > run_api_fixed.sh << EOF
#!/bin/bash
# Run the API server
source $VENV_PATH/bin/activate
echo "Starting API server..."
python api_server.py \$@
EOF

# Create GUI server script
cat > run_gui_fixed.sh << EOF
#!/bin/bash
# Run the GUI server
source $VENV_PATH/bin/activate
echo "Starting GUI server..."
python gui_server.py \$@
EOF

# Make scripts executable
chmod +x run_api_fixed.sh run_gui_fixed.sh

echo "======================================================"
echo "Setup complete! You can now run the servers with:"
echo "  ./run_api_fixed.sh"
echo "  ./run_gui_fixed.sh"
echo "======================================================"
echo ""
echo "Would you like to start the API server now? (y/n)"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    echo "Starting API server..."
    ./run_api_fixed.sh
fi