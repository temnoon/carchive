#!/bin/bash
# Include this in your .bashrc or .zshrc to automatically activate
# the correct environment when entering the project directory.
# Usage: source /path/to/carchive/shell_config.sh

# Define the carchive directory path
CARCHIVE_DIR="$HOME/archive/carchive"

# Function to check if we're in the carchive directory or a subdirectory
in_carchive_dir() {
  local current_dir="$(pwd)"
  if [[ "$current_dir" == "$CARCHIVE_DIR"* ]]; then
    return 0  # True
  else
    return 1  # False
  fi
}

# Function to activate carchive environment
activate_carchive() {
  if [ -f "$CARCHIVE_DIR/activate.sh" ]; then
    source "$CARCHIVE_DIR/activate.sh"
  else
    echo "Warning: Could not find $CARCHIVE_DIR/activate.sh"
  fi
}

# Set up auto-activation based on directory change
# For bash
if [ -n "$BASH_VERSION" ]; then
  cd() {
    builtin cd "$@"
    if in_carchive_dir; then
      activate_carchive
    fi
  }
fi

# For zsh
if [ -n "$ZSH_VERSION" ]; then
  chpwd() {
    if in_carchive_dir; then
      activate_carchive
    fi
  }
fi

# Alias for common commands
alias cd-carchive="cd $CARCHIVE_DIR && source $CARCHIVE_DIR/activate.sh"
alias carchive-setup="cd $CARCHIVE_DIR && python3.10 -m venv venv_310 && source venv_310/bin/activate && pip install -e ."

# Check if we're already in the carchive directory when sourcing this script
if in_carchive_dir; then
  activate_carchive
fi

echo "Carchive shell configuration loaded."
echo "Available commands:"
echo "  - cd-carchive: Go to carchive directory and activate environment"
echo "  - carchive-setup: Create a fresh Python 3.10 environment and install dependencies"