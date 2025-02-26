#!/bin/bash
# Run the GUI server with correct API URL
source ./mac_venv/bin/activate
# FLASK_ENV is deprecated in Flask 2.3, using only FLASK_DEBUG instead
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
" "$@"