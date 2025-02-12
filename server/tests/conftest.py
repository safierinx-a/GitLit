import os
import sys
from pathlib import Path

# Get the project root directory (server)
server_dir = Path(__file__).parent.parent.absolute()

# Add server directory to Python path if not already there
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

# Also add the parent directory to support 'server' package imports
parent_dir = server_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))
