#!/usr/bin/env python3

import os
import re
from pathlib import Path
from typing import Dict, List, Set


def find_python_files(directory: str) -> List[Path]:
    """Find all Python files in directory"""
    return list(Path(directory).rglob("*.py"))


def update_imports(file_path: Path, old_prefix: str, new_prefix: str) -> bool:
    """Update imports in a file"""
    with open(file_path, "r") as f:
        content = f.read()

    # Pattern for matching imports
    import_pattern = rf"from {old_prefix}([\w.]+) import|import {old_prefix}([\w.]+)"

    # Replace imports
    new_content = re.sub(
        import_pattern,
        lambda m: (
            f"from {new_prefix}{m.group(1)} import"
            if m.group(1)
            else f"import {new_prefix}{m.group(2)}"
        ),
        content,
    )

    if new_content != content:
        with open(file_path, "w") as f:
            f.write(new_content)
        return True
    return False


def main():
    # Import mappings
    mappings = {
        # Server mappings
        "server/src": {
            "backend.src": "",  # Remove backend.src prefix
            "..": "",  # Remove relative imports
        },
        # Controller mappings
        "controller/src": {
            "backend.src": "",  # Remove backend.src prefix
            "..": "",  # Remove relative imports
        },
    }

    updated_files: Set[Path] = set()

    for directory, prefix_map in mappings.items():
        python_files = find_python_files(directory)

        for file_path in python_files:
            for old_prefix, new_prefix in prefix_map.items():
                if update_imports(file_path, old_prefix, new_prefix):
                    updated_files.add(file_path)
                    print(f"Updated imports in {file_path}")

    print(f"\nUpdated {len(updated_files)} files")


if __name__ == "__main__":
    main()
