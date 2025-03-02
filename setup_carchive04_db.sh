#!/bin/bash
set -e

# Configuration
DB_NAME="carchive04_db"
DB_USER="carchive_app"
KEYCHAIN_SERVICE="carchvive"
KEYCHAIN_ACCOUNT="$DB_USER"
SCHEMA_FILE="carchive04_schema.sql"

# Function to get password from macOS Keychain
get_password_from_keychain() {
    # Try to get the password from Keychain
    DB_PASSWORD=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null)
    
    # If password not found, prompt the user and store it
    if [ -z "$DB_PASSWORD" ]; then
        echo "Password for $DB_USER not found in Keychain."
        read -s -p "Enter password for $DB_USER: " DB_PASSWORD
        echo
        
        # Store the password in Keychain for future use
        echo "Storing password in Keychain..."
        security add-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w "$DB_PASSWORD"
    else
        echo "Retrieved password from Keychain."
    fi
}

# Get the database password from Keychain
get_password_from_keychain

# Create database and user
echo "Creating database $DB_NAME and user $DB_USER..."
#sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;"

# Install pgvector extension
echo "Installing pgvector extension..."
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Apply schema
echo "Applying schema from $SCHEMA_FILE..."
PGPASSWORD="$DB_PASSWORD" psql -U $DB_USER -d $DB_NAME -f $SCHEMA_FILE

echo "Database setup complete!"
echo "You can now run the migration using:"
echo "poetry run carchive migrate chatgpt --db-name=$DB_NAME --db-user=$DB_USER chat2/conversations.json"
echo
echo "Note: The script will automatically use your password from the macOS Keychain."
echo "If you need to provide a different password, use the --db-password option."
