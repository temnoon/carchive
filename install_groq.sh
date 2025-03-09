#!/bin/bash
# Install the groq Python package

# Check if poetry is available
if command -v poetry &> /dev/null; then
    echo "Installing groq using poetry..."
    poetry add groq
    exit $?
fi

# If poetry is not available, use pip
echo "Poetry not found, using pip instead..."
python -m pip install groq

echo "Installation complete. Now you can add your Groq API key as an environment variable:"
echo "export GROQ_API_KEY=your_api_key_here"