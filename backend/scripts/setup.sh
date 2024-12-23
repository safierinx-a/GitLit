#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "Setting up LED Pattern System in $PROJECT_ROOT"

# Create virtual environment if it doesn't exist
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/venv"
fi

# Create requirements.txt if it doesn't exist
if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo "Creating requirements.txt..."
    cat > "$PROJECT_ROOT/requirements.txt" << 'EOF'
# Core dependencies
rpi-ws281x==4.3.4
numpy==1.24.2
PyYAML==6.0

# Testing
pytest==7.3.1
pytest-cov==4.1.0

# Development tools
black==23.9.1
flake8==6.1.0
mypy==1.5.1
EOF
fi

# Create activation script that works with both bash and sh
cat > "$PROJECT_ROOT/scripts/activate.sh" << EOF
#!/bin/sh
. "$PROJECT_ROOT/venv/bin/activate"
EOF

chmod +x "$PROJECT_ROOT/scripts/activate.sh"

echo "
Setup complete! To get started:

1. Activate the virtual environment:
   . $PROJECT_ROOT/scripts/activate.sh
   # or
   source $PROJECT_ROOT/scripts/activate.sh

2. Install requirements:
   pip install -r $PROJECT_ROOT/requirements.txt

3. Run LED tests:
   sudo -E env PATH=\$PATH python3 $PROJECT_ROOT/tests/test_led.py

4. Run pattern tests:
   sudo -E env PATH=\$PATH python3 $PROJECT_ROOT/tests/test_pattern_engine.py

5. Turn off LEDs:
   sudo -E env PATH=\$PATH python3 $PROJECT_ROOT/tests/test_led_off.py

Note: LED control requires sudo, but we preserve the virtual environment.
" 