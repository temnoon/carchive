#!/bin/bash

# Script to completely disable conda initialization in shells
# This removes the conda init blocks from .zshrc

echo "Creating backup of .zshrc..."
BACKUP_PATH=~/.zshrc.bak.$(date +%Y%m%d%H%M%S)
cp ~/.zshrc $BACKUP_PATH
echo "Backup created at $BACKUP_PATH"

echo "Removing conda initialization from .zshrc..."
# Remove the conda init block completely
sed -i '' '/# >>> conda initialize >>>/,/# <<< conda initialize <<</d' ~/.zshrc

# Also remove any manually added conda path
sed -i '' '/source ~\/.conda_path/d' ~/.zshrc
rm -f ~/.conda_path 2>/dev/null

echo "Conda has been completely removed from shell initialization."
echo "To use conda manually when needed, you'll need to run:"
echo "  source /Users/tem/anaconda3/bin/activate"
echo ""
echo "To restore your original config, run:"
echo "  cp $BACKUP_PATH ~/.zshrc"
echo ""
echo "Please restart your terminal for changes to take effect."