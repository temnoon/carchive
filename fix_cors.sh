#!/bin/bash

# Script to fix CORS issues between API and GUI servers

echo "Updating CORS configuration for API and GUI servers..."

# Create enhanced API server run script with explicit CORS settings
cat > run_api_with_cors.sh << EOF
#!/bin/bash
# Run the API server with expanded CORS settings
source ./mac_venv/bin/activate
export FLASK_ENV=development
export FLASK_DEBUG=1
echo "Starting API server with enhanced CORS support..."
python -c "
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('__file__')), 'src'))
from flask import Flask, jsonify
from flask_cors import CORS
from carchive2.api import create_app

app = create_app()
# Configure CORS explicitly with more permissive settings
CORS(app, resources={r'/*': {'origins': '*', 'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], 'allow_headers': '*'}})
app.run(host='127.0.0.1', port=5000, debug=True)
" "\$@"
EOF

# Create enhanced GUI server run script with correct API URL
cat > run_gui_with_cors.sh << EOF
#!/bin/bash
# Run the GUI server with correct API URL
source ./mac_venv/bin/activate
export FLASK_ENV=development
export FLASK_DEBUG=1
echo "Starting GUI server connecting to http://127.0.0.1:5000 API..."
python -c "
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath('__file__')), 'src'))
from carchive2.gui import create_app

app = create_app({
    'API_URL': 'http://127.0.0.1:5000',
    'DEBUG': True
})
app.run(host='127.0.0.1', port=5001, debug=True)
" "\$@"
EOF

# Make scripts executable
chmod +x run_api_with_cors.sh run_gui_with_cors.sh

echo "CORS fix complete!"
echo ""
echo "To run the API server with enhanced CORS:"
echo "  ./run_api_with_cors.sh"
echo ""
echo "To run the GUI server:"
echo "  ./run_gui_with_cors.sh"
echo ""
echo "Make sure to STOP any running API or GUI servers before starting these new ones!"