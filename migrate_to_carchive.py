#!/usr/bin/env python3
import glob
import re
import os
import shutil
from pathlib import Path
import sys

def update_file(file_path, project_dir):
    """Update imports and file path comments in a single file."""
    with open(file_path, "r", encoding="utf-8") as file:
        try:
            content = file.read()
        except UnicodeDecodeError:
            print(f"Warning: Could not read {file_path} as text. Skipping.")
            return False
    
    # Replace import statements
    updated_content = re.sub(
        r"from carchive2\.(\S+)", r"from carchive.\1", content
    )
    updated_content = re.sub(
        r"import carchive2(\s|\.)", r"import carchive\1", updated_content
    )
    
    # Update references to module in docstrings and comments
    updated_content = re.sub(
        r"carchive CLI", r"carchive CLI", updated_content
    )
    updated_content = re.sub(
        r"carchive API", r"carchive API", updated_content
    )
    
    # Generate relative path for comment if this is a source file
    src_dir = os.path.join(project_dir, "src")
    is_src_file = file_path.startswith(src_dir)
    
    # Handle different types of path comments
    old_path_pattern = r'([#"])\s*src/carchive2/(.+?)(\s|\n|"|$)'
    if re.search(old_path_pattern, updated_content):
        updated_content = re.sub(
            old_path_pattern,
            fr'\1 src/carchive/\2\3',
            updated_content
        )
    # If this is a source file and starts with Python code directly, add a comment
    elif is_src_file and not re.match(r'^\s*(#|"""|\'\'\')', updated_content):
        try:
            rel_path = os.path.relpath(file_path, src_dir)
            updated_content = f"# src/carchive/{rel_path}\n{updated_content}"
        except ValueError:
            # If we can't determine the relative path, just continue
            pass
    
    # Write updated content back
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(updated_content)
    
    return True

def update_pyproject(file_path):
    """Update pyproject.toml file."""
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    
    # Update package name
    content = re.sub(
        r'name = "carchive2"',
        r'name = "carchive"',
        content
    )
    
    # Update package path
    content = re.sub(
        r'packages = \[\{ include = "carchive2", from = "src" \}\]',
        r'packages = [{ include = "carchive", from = "src" }]',
        content
    )
    
    # Update CLI entrypoint
    content = re.sub(
        r'carchive = "carchive2\.cli\.main_cli:main"',
        r'carchive = "carchive.cli.main_cli:main"',
        content
    )
    
    # Write updated content back
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)
    
    print(f"Updated {file_path}")

def copy_and_migrate():
    """Copy files from carchive2 to carchive and update imports/references."""
    old_dir = "/Users/tem/archive/carchive2"
    new_dir = "/Users/tem/archive/carchive"
    
    # Copy all non-Python files
    print("Copying project files...")
    for root, dirs, files in os.walk(old_dir):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        
        # Skip __pycache__ directories
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
            
        # Skip virtual environment directories
        venv_dirs = [d for d in dirs if 'venv' in d or d.endswith('_venv')]
        for venv in venv_dirs:
            dirs.remove(venv)
            
        # Create corresponding directories in new location
        rel_path = os.path.relpath(root, old_dir)
        new_root = os.path.join(new_dir, rel_path)
        os.makedirs(new_root, exist_ok=True)
        
        for file in files:
            old_file = os.path.join(root, file)
            new_file = os.path.join(new_root, file)
            
            # Copy the file
            shutil.copy2(old_file, new_file)
    
    # Rename the src/carchive2 directory to src/carchive
    old_src = os.path.join(new_dir, "src/carchive2")
    new_src = os.path.join(new_dir, "src/carchive")
    
    if os.path.exists(old_src):
        # Create src/carchive directory if it doesn't exist
        os.makedirs(os.path.dirname(new_src), exist_ok=True)
        
        # Rename the directory
        if os.path.exists(new_src):
            shutil.rmtree(new_src)
        shutil.move(old_src, new_src)
        print(f"Renamed {old_src} to {new_src}")
    
    # Update imports and path comments in Python files
    print("Updating Python imports and references...")
    python_files = glob.glob(f"{new_dir}/**/*.py", recursive=True)
    
    updated_count = 0
    skipped_count = 0
    
    for file_path in python_files:
        if update_file(file_path, new_dir):
            updated_count += 1
        else:
            skipped_count += 1
    
    print(f"Updated {updated_count} Python files, skipped {skipped_count} files")
    
    # Update pyproject.toml
    pyproject_path = os.path.join(new_dir, "pyproject.toml")
    if os.path.exists(pyproject_path):
        update_pyproject(pyproject_path)
    
    print("Migration completed successfully!")
    print(f"The project has been migrated from {old_dir} to {new_dir}")
    print("Please review the changes and then run 'poetry install' in the new directory.")

if __name__ == "__main__":
    print("Starting migration from carchive2 to carchive...")
    copy_and_migrate()