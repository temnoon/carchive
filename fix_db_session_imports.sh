#!/bin/bash
# Script to fix db_session imports in all route files

# Function to fix imports in a file
fix_imports() {
    local file=$1
    echo "Checking $file..."
    
    # Check if file uses @db_session decorator
    if grep -q "@db_session" "$file"; then
        echo "File uses @db_session decorator"
        
        # Check import statement
        if grep -q "from carchive.database.session import get_session$" "$file"; then
            echo "Updating import to include db_session..."
            sed -i '' 's/from carchive.database.session import get_session$/from carchive.database.session import get_session, db_session/' "$file"
            echo "Fixed import in $file"
        elif grep -q "from carchive.database.session import db_session$" "$file"; then
            echo "Updating import to include get_session..."
            sed -i '' 's/from carchive.database.session import db_session$/from carchive.database.session import db_session, get_session/' "$file"
            echo "Fixed import in $file"
        elif ! grep -q "from carchive.database.session import .*db_session" "$file"; then
            echo "Adding db_session to imports..."
            sed -i '' 's/from carchive.database.session import/from carchive.database.session import db_session,/' "$file"
            echo "Fixed import in $file"
        else
            echo "Import statement already includes db_session"
        fi
    else
        echo "File does not use @db_session decorator"
    fi
}

# Find all route files using @db_session
echo "Finding route files using @db_session..."
files=$(grep -l "@db_session" src/carchive/api/routes/*.py)

# Fix imports in each file
for file in $files; do
    fix_imports "$file"
done

echo "All imports fixed!"