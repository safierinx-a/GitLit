#!/bin/bash

# Exit on error and print commands as they are executed
set -ex

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Store the absolute path of the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Get the project root directory (parent of script directory)
ROOT_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Script directory: $SCRIPT_DIR"
echo "Root directory: $ROOT_DIR"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

print_header "Installing System Dependencies"

# Update package lists
apt-get update

# Install Essentia and its dependencies
apt-get install -y \
    python3-essentia \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-yaml \
    python3-six \
    portaudio19-dev \
    libsndfile1-dev

print_header "Setting up Python Environment"

# Return to root and enter server directory
cd "$ROOT_DIR"
cd server
echo "Current directory for Python setup: $(pwd)"

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

print_header "Setup Complete"
echo -e "${GREEN}Server setup completed successfully!${NC}"
echo ""
echo "To start the server:"
echo "1. Activate the environment: cd server && source .venv/bin/activate"
echo "2. Run: uvicorn src.api.app:app --reload" 