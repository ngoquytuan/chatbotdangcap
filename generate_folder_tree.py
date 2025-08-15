#generate_folder_tree.py
import os
from pathlib import Path

def generate_tree(directory, output_file, prefix="", level=0):
    """Generate a tree structure of the directory and write to a file."""
    # Get all entries in the directory
    entries = sorted(Path(directory).iterdir())
    # Filter out hidden files and directories
    entries = [e for e in entries if not e.name.startswith('.')]
    
    # Open file in append mode if level > 0, else write mode
    mode = 'a' if level > 0 else 'w'
    with open(output_file, mode, encoding='utf-8') as f:
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            # Determine the connector symbol
            connector = "└── " if is_last else "├── "
            # Write the current entry
            f.write(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}\n")
            
            if entry.is_dir():
                # Determine the prefix for the next level
                new_prefix = prefix + ("    " if is_last else "│   ")
                # Recursively generate tree for subdirectory
                generate_tree(entry, output_file, new_prefix, level + 1)

def main():
    # Get current working directory
    current_dir = os.getcwd()
    output_file = "folder_tree.txt"
    
    # Generate the tree starting from current directory
    generate_tree(current_dir, output_file)
    
    print(f"Folder tree has been written to {output_file}")

if __name__ == "__main__":
    main()