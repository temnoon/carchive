#!/bin/bash

# Script to fix the conda base environment pydantic issue
# This will properly install pydantic v2 in the base environment
# and remove conflicting installations

echo "Fixing conda base environment pydantic issues..."

# Uninstall all pydantic-related packages from base environment
pip uninstall -y pydantic pydantic-core pydantic-settings anaconda-cloud-auth

# Install pydantic v2 which has AliasGenerator
pip install pydantic==2.10.3

# Reinstall anaconda-cloud-auth which depends on pydantic
pip install anaconda-cloud-auth

echo "Base environment fixed. Please open a new terminal to verify the fix."