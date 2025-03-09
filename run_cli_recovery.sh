#!/bin/bash
# Run the CLI with the recovery environment
source ./venv_recovery/bin/activate
echo "Starting carchive CLI with recovery environment..."
poetry run carchive "$@"
