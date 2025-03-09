#!/bin/bash
# Run the CLI with the recovery environment and all fixes applied

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Run CLI command
echo "Running carchive CLI with recovery environment..."
python -m carchive.cli.main_cli "$@"