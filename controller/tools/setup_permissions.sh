#!/bin/bash

# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup_permissions.sh)"
    exit 1
fi

# Get the username that ran sudo
SUDO_USER=${SUDO_USER:-$(whoami)}

# Create gpio group if it doesn't exist
getent group gpio || groupadd gpio

# Add user to required groups
usermod -a -G gpio,spi,i2c,video "$SUDO_USER"

# Create udev rules for GPIO access
cat > /etc/udev/rules.d/99-gpio.rules << EOF
SUBSYSTEM=="gpio*", PROGRAM="/bin/sh -c 'chown -R root:gpio /sys/class/gpio && chmod -R 770 /sys/class/gpio; chown -R root:gpio /sys/devices/virtual/gpio && chmod -R 770 /sys/devices/virtual/gpio'"
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /dev/%k && chmod 770 /dev/%k'"
EOF

# Create udev rules for LED device
cat > /etc/udev/rules.d/99-led.rules << EOF
SUBSYSTEM=="mem", KERNEL=="mem", GROUP="gpio", MODE="0660"
SUBSYSTEM=="pwm*", GROUP="gpio", MODE="0660"
EOF

# Set up PWM permissions
cat > /etc/udev/rules.d/99-pwm.rules << EOF
SUBSYSTEM=="pwm*", PROGRAM="/bin/sh -c 'chown -R root:gpio /sys/class/pwm && chmod -R 770 /sys/class/pwm; chown -R root:gpio /sys/devices/platform/pwm* && chmod -R 770 /sys/devices/platform/pwm*'"
EOF

# Give gpio group access to /dev/mem
cat > /etc/udev/rules.d/99-mem.rules << EOF
KERNEL=="mem", GROUP="gpio", MODE="0660"
EOF

# Create a systemd tmpfiles configuration for persistent GPIO permissions
cat > /etc/tmpfiles.d/gpio.conf << EOF
d /sys/class/gpio 0770 root gpio
d /sys/devices/virtual/gpio 0770 root gpio
d /sys/class/pwm 0770 root gpio
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Create gpio device if it doesn't exist
if [ ! -e /dev/gpiomem ]; then
    mknod /dev/gpiomem c 243 0
fi
chown root:gpio /dev/gpiomem
chmod 660 /dev/gpiomem

# Set permissions for /dev/mem
chown root:gpio /dev/mem
chmod 660 /dev/mem

echo "Permissions setup complete! Please reboot your Raspberry Pi for changes to take effect." 