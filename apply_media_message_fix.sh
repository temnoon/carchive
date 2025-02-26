#!/bin/bash

# This script applies the media-message association fix to the database and codebase

echo "Applying media-message relationship fix..."

# Ensure the script is executable
chmod +x scripts/create_message_media_table.py
chmod +x scripts/fix_media_message_schema.py

# Activate the virtual environment
source ./mac_venv/bin/activate

echo "Step 1: Creating message_media association table in database..."
python scripts/create_message_media_table.py
if [ $? -ne 0 ]; then
    echo "Failed to create message_media table. Exiting."
    exit 1
fi

echo "Step 2: Updating code models and API to use the new association table..."
python scripts/fix_media_message_schema.py
if [ $? -ne 0 ]; then
    echo "Failed to update models and API. Exiting."
    exit 1
fi

echo "Step 3: Restarting the servers with the new schema..."
./restart_servers.sh

echo "Media-message relationship fix has been applied and servers restarted."
echo "You should now see media items associated with messages in the web interface."