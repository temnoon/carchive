#!/bin/bash
# Silent render script - suppresses non-essential logging messages

# Capture all arguments
args="$@"

# Run carchive render with stderr redirected to null
poetry run carchive render $args 2>/dev/null