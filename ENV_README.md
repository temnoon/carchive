# Carchive Environment Management

This document provides guidance on managing the Python environment for the Carchive project.

## Requirements

- Python 3.10 (required, not 3.13 or other versions)
- PostgreSQL with pgvector extension

## Setup Instructions

### 1. Create a Python 3.10 Environment

```bash
# Run the environment creation script
./create_py310_env.sh
```

This script will:
- Create a new Python 3.10 virtual environment in `venv_310/`
- Install all required dependencies
- Set up the package in development mode

### 2. Activate the Environment

```bash
# Activate the environment properly
source activate.sh
```

The activation script will:
- Activate the Python 3.10 virtual environment
- Set the correct PYTHONPATH
- Check for critical dependencies
- Provide helpful aliases

### 3. Fix Environment Issues

If you encounter dependency problems:

```bash
# Fix common environment issues
./fix_env.sh
```

This will:
- Install missing dependencies
- Fix version conflicts
- Ensure the PYTHONPATH is set correctly

## Running the Servers

### Standard Method (Using CLI)

```bash
# Start both servers using the CLI
./run_servers.sh
```

### Direct Method (Bypassing CLI)

If the CLI doesn't work:

```bash
# Start servers directly
./run_direct.sh
```

## Troubleshooting

1. **ModuleNotFoundError: No module named 'rich'**
   - Run `./fix_env.sh` to install missing dependencies

2. **Python version issues**
   - Ensure you're using Python 3.10, not 3.13
   - Check with `python --version` when the environment is activated
   - Run `./create_py310_env.sh` if needed

3. **Path issues**
   - The environment may not be finding the carchive package
   - Run `export PYTHONPATH="$PWD/src:$PYTHONPATH"`

4. **Server startup failures**
   - Check the error message for missing dependencies
   - Try the direct method: `./run_direct.sh`