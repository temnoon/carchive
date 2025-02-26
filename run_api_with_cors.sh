#!/bin/bash
# Run the API server with expanded CORS settings
source ./mac_venv/bin/activate
# FLASK_ENV is deprecated in Flask 2.3, using only FLASK_DEBUG instead
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
" "$@"