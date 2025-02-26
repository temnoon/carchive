#!/bin/bash

# Script to temporarily disable conda auto-initialization
# This creates a backup of your .zshrc and comments out the conda init block

echo "Creating backup of .zshrc..."
cp ~/.zshrc ~/.zshrc.bak.$(date +%Y%m%d%H%M%S)

echo "Modifying .zshrc to disable conda auto-initialization..."
# Comment out the conda init block
sed -i.bak '
/# >>> conda initialize >>>/,/# <<< conda initialize <<</ s/^/#DISABLED_CONDA# /
' ~/.zshrc

echo ".zshrc modified. The conda initialization has been commented out."
echo "Your original .zshrc has been backed up at ~/.zshrc.bak.*"
echo ""
echo "To manually activate conda when needed, you can run:"
echo "source /Users/tem/anaconda3/bin/activate"
echo ""
echo "To restore the original behavior, run:"
echo "cp ~/.zshrc.bak.* ~/.zshrc"