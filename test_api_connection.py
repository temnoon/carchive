#!/usr/bin/env python3
"""
Test script to verify the API and GUI servers are running.
"""

import sys
import requests
import json

def test_server(url, name):
    """Test if a server is reachable at the given URL."""
    try:
        response = requests.get(url, timeout=5)
        print(f"{name} server is running at {url}")
        print(f"Status code: {response.status_code}")
        try:
            data = response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")
        except ValueError:
            print(f"Response text: {response.text[:200]}")
        return True
    except Exception as e:
        print(f"Error connecting to {name} server at {url}: {e}")
        return False

def main():
    """Test both API and GUI servers."""
    api_success = test_server("http://127.0.0.1:8000/api/health", "API")
    gui_success = test_server("http://127.0.0.1:8001/", "GUI")
    
    if api_success and gui_success:
        print("\nBoth servers are running successfully!")
        return 0
    else:
        print("\nServer check failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())