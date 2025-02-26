#!/bin/bash

# Fix conda conflicts by properly initializing the correct conda installation
echo "Fixing conda initialization..."

# Restore original .zshrc
if [ -f ~/.zshrc.bak.* ]; then
  LATEST_BACKUP=$(ls -t ~/.zshrc.bak.* | head -1)
  echo "Restoring original .zshrc from $LATEST_BACKUP"
  cp "$LATEST_BACKUP" ~/.zshrc
fi

# Check which conda installations exist
echo "Found conda installations:"
which -a conda

# Choose the Anaconda3 installation that was working before
echo "Setting up Anaconda3 installation..."

# Put in a specific conda path to ensure the correct one is used
cat > ~/.conda_path << EOF
# This file specifies which conda installation to use
export CONDA_EXE="/Users/tem/anaconda3/bin/conda"
export CONDA_PREFIX="/Users/tem/anaconda3"
export PATH="/Users/tem/anaconda3/bin:$PATH"
EOF

# Add source for conda path to zshrc
echo "Updating .zshrc to use the specific conda installation..."
if ! grep -q "source ~/.conda_path" ~/.zshrc; then
  echo "source ~/.conda_path" >> ~/.zshrc
fi

# Initialize conda for zsh
echo "Initializing conda for zsh..."
/Users/tem/anaconda3/bin/conda init zsh

echo "Conda initialization complete. Please close this terminal and open a new one."
echo "Then, run: conda activate carchive2_env"