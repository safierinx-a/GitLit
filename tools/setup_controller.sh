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
    swig

# Install audio dependencies
apt-get install -y \
    libasound2-dev \
    libportaudio2 \
    alsa-utils

print_header "Setting up Audio Configuration"

# Add user to audio group
usermod -a -G audio $SUDO_USER

# Configure ALSA for better performance
cat > /etc/asound.conf << EOL
pcm.!default {
    type hw
    card 0
}

ctl.!default {
    type hw
    card 0
}
EOL

print_header "Setting up LED Dependencies"

# Enable SPI if not already enabled
if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    echo "SPI interface enabled. A reboot will be required."
fi

# Create udev rule for LED access
cat > /etc/udev/rules.d/92-led.rules << EOL
SUBSYSTEM=="pwm*", PROGRAM="/bin/sh -c '\
        chown -R root:gpio /sys/class/pwm && chmod -R 770 /sys/class/pwm;\
        chown -R root:gpio /sys/devices/platform/pwm* && chmod -R 770 /sys/devices/platform/pwm*\
'"
EOL

print_header "Setting up Python Environment"

# Switch to the controller directory
cd "$(dirname "$0")/../controller"

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

print_header "Setup Complete"
echo -e "${GREEN}Controller setup completed successfully!${NC}"
echo ""
echo "Important notes:"
echo "1. A system reboot is required to apply all changes"
echo "2. After reboot, the LED strip will be accessible"
echo "3. Audio capture has been configured for optimal performance"
echo ""
echo "To start the controller:"
echo "1. Reboot the system: sudo reboot"
echo "2. After reboot: cd controller && source .venv/bin/activate"
echo "3. Run: python src/client/audio_client.py" 