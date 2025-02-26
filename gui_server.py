#!/usr/bin/env python3
"""
Standalone script to run the carchive GUI web interface.
"""

import os
import sys
import argparse

# Add src directory to Python path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import create_app function
from carchive.gui import create_app

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the carchive web interface.')
    parser.add_argument('--host', '-H', default='127.0.0.1', help='Host to bind to.')
    parser.add_argument('--port', '-p', type=int, default=5001, help='Port to bind to.')
    parser.add_argument('--api-url', '-a', default='http://localhost:5000', help='URL for the API server.')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode.')
    return parser.parse_args()

def main():
    """Run the web interface."""
    args = parse_args()
    
    # Set Flask environment
    if args.debug:
        os.environ['FLASK_ENV'] = 'development'
    
    # Create and run Flask app
    app = create_app({
        'API_URL': args.api_url,
        'DEBUG': args.debug
    })
    
    print(f"Starting Web Interface at http://{args.host}:{args.port}")
    print(f"API URL: {args.api_url}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()