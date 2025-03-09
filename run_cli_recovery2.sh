#!/bin/bash
# Run the CLI with the recovery environment
source ./venv_recovery2/bin/activate
echo "Starting carchive CLI with recovery environment..."
cd /Users/tem/archive/carchive
poetry run carchive "$@"
