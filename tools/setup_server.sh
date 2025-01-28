#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

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
    cmake \
    build-essential \
    libfftw3-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libyaml-dev

print_header "Building Essentia from Source"

# Clone Essentia repository
if [ ! -d "essentia" ]; then
    git clone https://github.com/MTG/essentia.git
    cd essentia
    git checkout master
    
    # Configure and build
    mkdir -p build
    cd build
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DESSENTIA_PYTHON_EXTENSIONS=ON \
          -DBUILD_EXAMPLES=OFF \
          -DBUILD_TESTING=OFF \
          ..
    
    # Compile with reduced parallel jobs for stability
    make -j2
    make install
    ldconfig
    cd ../..
fi

print_header "Setting up Python Environment"

# Switch to the server directory
cd "$(dirname "$0")/../server"

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