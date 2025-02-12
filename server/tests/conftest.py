import os
import sys

# Add the server directory to Python path
server_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if server_dir not in sys.path:
    sys.path.append(server_dir)
