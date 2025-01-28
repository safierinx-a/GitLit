#!/bin/bash

# Exit on error and print commands as they are executed
set -ex

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
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

# Install system dependencies
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    portaudio19-dev \
    libatlas-base-dev \
    gcc \
    make \
    git \
    swig \
    build-essential \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libyaml-dev \
    python3-numpy-dev \
    python3-yaml \
    libpython3-dev \
    pkg-config

# Create python symlink if it doesn't exist
if ! command -v python &> /dev/null; then
    echo "Creating python symlink..."
    ln -s $(which python3) /usr/local/bin/python
fi

print_header "Building Essentia from Source"

# Create and enter external directory
cd "$ROOT_DIR"
echo "Current directory before creating external: $(pwd)"
mkdir -p external
cd external
echo "Current directory after entering external: $(pwd)"

# Remove existing essentia directory if it exists
if [ -d "essentia" ]; then
    echo "Removing existing essentia directory"
    rm -rf essentia
fi

# Clone Essentia
echo "Cloning Essentia repository"
git clone https://github.com/MTG/essentia.git
cd essentia
echo "Current directory after entering essentia: $(pwd)"

# List contents to verify clone
echo "Contents of essentia directory:"
ls -la

# Make waf executable
chmod +x waf

# Configure and build using waf
echo "Configuring Essentia build..."
./waf configure --build-static --with-python --python=$(which python3)
echo "Building Essentia..."
./waf
echo "Installing Essentia..."
./waf install
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