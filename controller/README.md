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

## Usage

```bash
# Start the controller
python -m client.led_client --host SERVER_IP
```

## Hardware Requirements

- Raspberry Pi (3 or newer recommended)
- WS2812B LED strip
- 5V power supply (sized for LED count)
- Level shifter (3.3V to 5V)
