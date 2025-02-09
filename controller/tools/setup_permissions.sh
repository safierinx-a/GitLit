#!/bin/bash

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup_permissions.sh)"
    exit 1
fi

# Get the username that ran sudo
SUDO_USER=${SUDO_USER:-$(whoami)}

# Add user to required groups
usermod -a -G gpio,spi,i2c "$SUDO_USER"

# Create udev rules for GPIO access
cat > /etc/udev/rules.d/99-gpio.rules << EOF
SUBSYSTEM=="gpio*", PROGRAM="/bin/sh -c 'chown -R root:gpio /sys/class/gpio && chmod -R 770 /sys/class/gpio; chown -R root:gpio /sys/devices/virtual/gpio && chmod -R 770 /sys/devices/virtual/gpio'"
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /dev/%k && chmod 770 /dev/%k'"
EOF

# Create udev rules for LED device
cat > /etc/udev/rules.d/99-led.rules << EOF
SUBSYSTEM=="mem", KERNEL=="mem", GROUP="gpio", MODE="0660"
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

echo "Permissions setup complete! Please log out and back in for changes to take effect." 