#!/usr/bin/env python3
"""
Script to analyze the chat archive and extract key information about:
1. DALL-E asset references in messages
2. LaTeX content in messages
3. File references and their existence

This script helps ensure our rendering changes correctly handle all content types.
"""
import json
import os
import re
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Run a shell command and return its output."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout

def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def examine_conversations_with_assets():
    """Find conversations with DALL-E asset references."""
    print_section("CONVERSATIONS WITH DALL-E ASSET REFERENCES")
    
    # Search the archive for asset references
    command = "poetry run carchive archive search 'chat2.zip' '[Asset: file-'"
    output = run_command(command)
    
    # Print results
    print(output)
    
    # Extract conversation IDs and save to file
    conversation_ids = re.findall(r'Conversation ID: ([a-f0-9-]+)', output)
    if conversation_ids:
        with open("test_outputs/dalle_conversations.txt", "w") as f:
            for conv_id in conversation_ids:
                f.write(f"{conv_id}\n")
        print(f"Found {len(conversation_ids)} conversations with asset references")
        print(f"First few IDs: {', '.join(conversation_ids[:3])}")
    else:
        print("No conversations with asset references found")

def examine_conversations_with_latex():
    """Find conversations with LaTeX content."""
    print_section("CONVERSATIONS WITH LATEX CONTENT")
    
    # Search for common LaTeX patterns
    latex_patterns = [
        '\\\\begin{equation}',
        '\\\\frac{',
        '\\\\sum_',
        '\\\\int_',
        '\\\\mathbf',
        '\\\\mathrm'
    ]
    
    all_conversation_ids = set()
    
    for pattern in latex_patterns:
        print(f"\nSearching for pattern: {pattern}")
        command = f"poetry run carchive archive search 'chat2.zip' '{pattern}'"
        output = run_command(command)
        
        # Extract conversation IDs
        conversation_ids = re.findall(r'Conversation ID: ([a-f0-9-]+)', output)
        all_conversation_ids.update(conversation_ids)
        
        print(f"Found {len(conversation_ids)} conversations with this pattern")
    
    # Save to file
    if all_conversation_ids:
        with open("test_outputs/latex_conversations.txt", "w") as f:
            for conv_id in all_conversation_ids:
                f.write(f"{conv_id}\n")
        print(f"\nTotal unique conversations with LaTeX: {len(all_conversation_ids)}")
        print(f"First few IDs: {', '.join(list(all_conversation_ids)[:3])}")
    else:
        print("\nNo conversations with LaTeX found")

def examine_dalle_files():
    """Examine DALL-E generated files in the archive."""
    print_section("DALL-E FILES IN ARCHIVE")
    
    command = "poetry run carchive archive list-media 'chat2.zip'"
    output = run_command(command)
    
    # Find DALL-E files
    dalle_files = re.findall(r'(file-[a-zA-Z0-9]+-[a-f0-9-]+\.webp)', output)
    
    if dalle_files:
        print(f"Found {len(dalle_files)} potential DALL-E files")
        print("Sample files:")
        for file in dalle_files[:5]:
            print(f"  {file}")
            
        # Extract file IDs
        file_ids = [re.match(r'file-([a-zA-Z0-9]+)', file).group(1) for file in dalle_files if re.match(r'file-([a-zA-Z0-9]+)', file)]
        
        print(f"\nExtracted {len(file_ids)} file IDs")
        print("Sample file IDs:")
        for file_id in file_ids[:5]:
            print(f"  file-{file_id}")
            
        # Save to file
        with open("test_outputs/dalle_file_ids.txt", "w") as f:
            for file_id in file_ids:
                f.write(f"file-{file_id}\n")
    else:
        print("No DALL-E files found in the archive")

def main():
    """Main function."""
    # Create output directory
    os.makedirs("test_outputs", exist_ok=True)
    
    # Run analysis
    examine_conversations_with_assets()
    examine_conversations_with_latex()
    examine_dalle_files()
    
    print("\nAnalysis complete. Check test_outputs/ directory for results.")

if __name__ == "__main__":
    main()