#\!/bin/bash
set -e

# Configuration
DB_NAME="carchive04_db"
DB_USER="carchive_app"
DB_PASSWORD="hozcan-1ciksi-Wivkab"  # Change this in production
SCHEMA_FILE="carchive04_schema.sql"

# Create database and user
echo "Creating database $DB_NAME and user $DB_USER..."
#sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME WITH OWNER $DB_USER;"

# Install pgvector extension
echo "Installing pgvector extension..."
sudo -u postgres psql -d $DB_NAME -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Apply schema
echo "Applying schema from $SCHEMA_FILE..."
psql -U $DB_USER -d $DB_NAME -f $SCHEMA_FILE

echo "Database setup complete\!"
echo "You can now run the migration using:"
echo "poetry run carchive migrate chatgpt --db-name=$DB_NAME --db-user=$DB_USER --db-password=$DB_PASSWORD chat2/conversations.json"
