#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

# Function to setup Python environment
setup_python_env() {
    local dir=$1
    print_header "Setting up $dir environment"
    
    cd $dir
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -e ".[dev]"
    
    # Deactivate virtual environment
    deactivate
    
    cd ..
}

# Function to setup frontend environment
setup_frontend() {
    print_header "Setting up frontend environment"
    
    cd frontend
    
    # Install npm dependencies
    if [ -f "package.json" ]; then
        echo "Installing npm dependencies..."
        npm install
    else
        echo -e "${RED}Warning: package.json not found${NC}"
    fi
    
    cd ..
}

# Main setup
print_header "GitLit Development Environment Setup"

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if (( $(echo "$python_version 3.11" | awk '{print ($1 < $2)}') )); then
    echo -e "${RED}Error: Python 3.11 or higher is required${NC}"
    exit 1
fi

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

# Setup server environment
setup_python_env "server"

# Setup controller environment
setup_python_env "controller"

# Setup frontend environment
setup_frontend

print_header "Setup Complete"
echo -e "${GREEN}Development environment setup successfully!${NC}"
echo ""
echo "To start development:"
echo "1. Server:   cd server && source .venv/bin/activate"
echo "2. Controller: cd controller && source .venv/bin/activate"
echo "3. Frontend: cd frontend && npm run dev"
``` 