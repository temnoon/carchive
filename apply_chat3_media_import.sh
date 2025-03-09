#!/bin/bash
# apply_chat3_media_import.sh
#
# Script to apply chat3 media restructuring:
# 1. Reset the media database records
# 2. Import media files from chat3 archive
# 3. Update environment to use the new media structure

set -e  # Exit on error

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Set up environment
source venv_310/bin/activate
export PYTHONPATH=$PWD/src:$PYTHONPATH

echo -e "${YELLOW}Step 1: Run the database media reset in dry-run mode${NC}"
echo "This will show what records would be deleted without making changes"
python reset_media_db.py --dry-run

echo -e "${YELLOW}Do you want to continue with the actual database reset? (y/n)${NC}"
read -r answer
if [[ "$answer" != "y" ]]; then
  echo -e "${RED}Import cancelled.${NC}"
  exit 0
fi

echo -e "${YELLOW}Step 2: Run the actual database reset${NC}"
python reset_media_db.py

echo -e "${YELLOW}Step 3: Run the chat3 media import in dry-run mode${NC}"
echo "This will analyze what needs to be imported without making changes"
python import_chat3_media.py --source-dir chat3 --target-dir media_new --dry-run

echo -e "${YELLOW}Do you want to continue with the actual import? (y/n)${NC}"
read -r answer
if [[ "$answer" != "y" ]]; then
  echo -e "${RED}Import cancelled.${NC}"
  exit 0
fi

echo -e "${YELLOW}Step 4: Run the actual chat3 media import${NC}"
python import_chat3_media.py --source-dir chat3 --target-dir media_new

echo -e "${GREEN}Media import complete!${NC}"
echo "All media files from chat3 have been imported to the media_new directory structure."
echo "If everything looks good, you should update your settings to use the new media structure:"
echo ""
echo "1. Edit your .env file to set: CARCHIVE_MEDIA_DIR=media_new"
echo "2. Restart your servers with: carchive server stop && carchive server start-all"