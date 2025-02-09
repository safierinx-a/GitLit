# GitLit Controller

LED hardware control and pattern rendering for the GitLit system.

## Features

- Direct LED strip control via GPIO
- WebSocket client for pattern updates
- Hardware safety checks
- Pattern rendering

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .
```

## Hardware Setup

### Permissions Setup (Raspberry Pi)

Before running the controller, you need to set up proper permissions for GPIO access:

```bash
# Run the permissions setup script (only needed once)
sudo ./tools/setup_permissions.sh

# Log out and log back in for changes to take effect
```

## Usage

```bash
# Start the controller (no sudo needed after permissions setup)
python -m client.led_client --host SERVER_IP
```

## Hardware Requirements

- Raspberry Pi (3 or newer recommended)
- WS2812B LED strip
- 5V power supply (sized for LED count)
- Level shifter (3.3V to 5V)
