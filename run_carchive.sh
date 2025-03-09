#!/bin/bash
# Run carchive commands with the recovery environment

# Activate the recovery environment
source ./venv_recovery2/bin/activate

# Run carchive command
carchive "$@"