#!/usr/bin/env python3
"""
Standalone script to run the carchive API server.
"""

import os
import sys
import argparse

# Add src directory to Python path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import create_app function
from carchive.api import create_app

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the carchive API server.')
    parser.add_argument('--host', '-H', default='127.0.0.1', help='Host to bind to.')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to bind to.')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode.')
    return parser.parse_args()

def main():
    """Run the API server."""
    args = parse_args()
    
    # Set Flask environment
    if args.debug:
        os.environ['FLASK_ENV'] = 'development'
    
    # Create and run Flask app
    app = create_app()
    print(f"Starting API server at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()