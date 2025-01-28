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

# Install build dependencies
apt-get install -y \
    build-essential \
    libeigen3-dev \
    libyaml-dev \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libchromaprint-dev \
    python3-dev \
    python3-numpy \
    python3-yaml \
    python3-six \
    python3-pip \
    python3-venv \
    pkg-config

print_header "Building Essentia from Source"

# Create and enter external directory
cd "$ROOT_DIR"
mkdir -p external
cd external

# Clone Essentia with submodules
echo "Cloning Essentia repository"
git clone --recursive https://github.com/MTG/essentia.git
cd essentia

# Configure and build using waf
echo "Configuring Essentia build..."
python3 waf configure --build-static --with-python
echo "Building Essentia..."
python3 waf
echo "Installing Essentia..."
python3 waf install
ldconfig

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