# Environment Management Guide

This guide covers the environment management features in carchive, including setup, dependency management, and issue resolution.

## Overview

Carchive provides a unified CLI interface for managing Python environments with the `carchive env` command. This replaces multiple shell scripts and provides consistent functionality across platforms.

## Environment Commands

### Viewing Environment Information

```bash
# Display information about the current environment
poetry run carchive env info
```

This shows Python version, platform details, active virtual environment, and installed package versions.

### Setting Up a New Environment

```bash
# Create a standard environment
poetry run carchive env setup

# Create a Mac-optimized environment
poetry run carchive env setup --env-type=mac-optimized --path=./mac_venv

# Create a minimal environment with only core dependencies
poetry run carchive env setup --env-type=minimal

# Force recreation of an existing environment
poetry run carchive env setup --force

# Setup without creating run scripts
poetry run carchive env setup --no-run-scripts

# Setup without creating .env file
poetry run carchive env setup --no-dotenv
```

### Fixing Common Issues

```bash
# Fix dependency conflicts
poetry run carchive env fix-dependencies

# Fix CORS settings for API and GUI
poetry run carchive env fix-cors

# Check for common environment issues
poetry run carchive env check
```

## Environment Types

### Standard Environment

The default environment type with all required dependencies, suitable for most users.

```bash
poetry run carchive env setup --env-type=standard
```

### Mac-Optimized Environment

An environment specifically optimized for macOS with performance tweaks, particularly for Apple Silicon.

```bash
poetry run carchive env setup --env-type=mac-optimized
```

Special optimizations include:
- Memory optimizations for unified memory
- Metal Performance Shaders (MPS) support
- OpenMP thread optimizations
- PostgreSQL implementation optimizations

### Minimal Environment

A lightweight environment with only the core dependencies required to run carchive.

```bash
poetry run carchive env setup --env-type=minimal
```

## Common Issues and Solutions

### Dependency Conflicts

If you encounter dependency conflicts (particularly with pydantic or flask):

```bash
poetry run carchive env fix-dependencies
```

This command:
- Reinstalls key packages in the correct order
- Forces specific versions known to work together
- Reinstalls carchive in development mode

### CORS Issues

If you encounter CORS (Cross-Origin Resource Sharing) errors when accessing the API from web clients:

```bash
poetry run carchive env fix-cors
```

This automatically configures both API and GUI servers to allow cross-origin requests.

### Multiple Environment Management

You can maintain multiple environments for different purposes:

```bash
# Create a development environment
poetry run carchive env setup --path=./dev_venv

# Create a testing environment
poetry run carchive env setup --path=./test_venv --env-type=minimal
```

Each environment will have its own run scripts with appropriate names.

## Legacy Scripts

The following legacy shell scripts have been replaced by the `carchive env` command:

- `setup_venv.sh` → `carchive env setup`
- `setup_mac_optimized_env.sh` → `carchive env setup --env-type=mac-optimized`
- `fix_dependencies.sh` → `carchive env setup fix-dependencies`
- `fix_cors.sh` → `carchive env fix-cors`
- `install_missing_deps.sh` → `carchive env fix-dependencies`
- `comprehensive_fix.sh` → `carchive env setup --force && carchive env fix-dependencies`

## Integration with Other Commands

The environment management commands integrate well with other carchive features:

```bash
# Complete setup and validation workflow
poetry run carchive env setup
poetry run carchive env check
poetry run carchive db validate
```

## Troubleshooting

If you encounter issues with environment setup:

1. Check Python version: `python --version` (3.8+ recommended)
2. Ensure pip is up to date: `pip install --upgrade pip`
3. Verify virtual environment is active
4. Run environment check: `carchive env check`

For dependency conflicts, try:
```bash
# Force reinstallation of all requirements
pip install --force-reinstall -r requirements.txt
```

## FAQs

### Q: When should I use mac-optimized vs standard?
A: Use mac-optimized if you're on a Mac, especially Apple Silicon (M1/M2/M3), for better performance.

### Q: How do I update dependencies in an existing environment?
A: Run `carchive env fix-dependencies` to update to the latest compatible versions.

### Q: Can I use this with conda?
A: The commands work best with venv environments. If using conda, create a dedicated environment first.