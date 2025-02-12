import os
import sys
from pathlib import Path
import pytest
import yaml

# Get the project root directory (server)
server_dir = Path(__file__).parent.parent.absolute()

# Add server directory to Python path if not already there
if str(server_dir) not in sys.path:
    sys.path.insert(0, str(server_dir))

# Also add the parent directory to support 'server' package imports
parent_dir = server_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))


@pytest.fixture
def led_config():
    """Default LED configuration for testing"""
    return {"led_strip": {"count": 60, "pin": 18, "brightness": 1.0, "type": "WS2812B"}}


@pytest.fixture
def config_file(tmp_path, led_config):
    """Create a temporary config file for testing"""
    config_path = tmp_path / "led_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(led_config, f)
    return config_path
