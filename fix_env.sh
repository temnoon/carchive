#!/bin/bash
# Script to fix Python environment issues

# Activate the Python 3.10 environment
source venv_310/bin/activate

echo "Fixing dependencies for carchive in Python 3.10 environment..."

# Install core dependencies that might be missing
pip install rich typer flask flask-cors sqlalchemy psycopg2-binary pydantic

# Explicitly install key packages with versions that work together
pip install werkzeug==2.2.3 flask==2.2.5 pydantic==1.10.8

# Fix the import error by installing additional packages
pip install httpx sniffio typing-extensions keyring python-dotenv

# Install development tools
pip install pytest black isort

# Set the PYTHONPATH to ensure the carchive package is found
export PYTHONPATH=$PWD/src:$PYTHONPATH

# Create a custom .pth file in the site-packages to ensure the src directory is always in the path
echo "Creating .pth file to add src directory to Python path..."
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
echo "$PWD/src" > "$SITE_PACKAGES/carchive.pth"

echo "Verifying carchive package can be imported..."
python -c "import carchive; print(f'carchive package found at: {carchive.__file__}')"

echo "Verifying CLI dependencies..."
python -c "import typer, rich, flask, sqlalchemy, pydantic; print('All core CLI dependencies available')"

echo "Environment fixed successfully. You should now be able to run:"
echo "  carchive server status"
echo "  ./run_servers.sh"