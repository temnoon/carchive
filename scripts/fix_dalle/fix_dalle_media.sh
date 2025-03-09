#!/bin/bash
# Script to fix DALL-E generated images in the database
# This script runs all needed Python scripts to properly mark, link, and associate
# DALL-E generated images with their messages.

set -e

echo "===== Step 1: Fixing original file IDs for DALL-E images ====="
python scripts/fix_dalle/fix_original_file_ids.py

echo "===== Step 2: Identifying and marking DALL-E generated images ====="
python scripts/fix_dalle/find_dalle_images.py

echo "===== Step 3: Updating file paths for DALL-E images ====="
python scripts/fix_dalle/update_media_paths.py

echo "===== Step 4: Associating DALL-E images with messages ====="
python scripts/fix_dalle/associate_images.py

echo "===== Step 5: Testing DALL-E image rendering ====="
python tests/test_dalle_rendering.py

echo "===== DALL-E media fix complete! ====="
echo "You can now render conversations with DALL-E generated images."
echo "Example: poetry run carchive render conversation <conversation_id>"
echo ""
echo "Test HTML files have been saved to the test_output directory."
echo "Review them to ensure images are rendering correctly."