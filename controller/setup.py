from setuptools import setup, find_packages
import sys

# Determine if we're on a Raspberry Pi
is_raspberry_pi = False
try:
    with open("/proc/cpuinfo", "r") as f:
        for line in f:
            if line.startswith("Model"):
                if "Raspberry Pi" in line:
                    is_raspberry_pi = True
                break
except:
    pass

# Base requirements
install_requires = [
    "numpy>=1.24.0",
    "websockets>=11.0.3",
]

# Hardware-specific requirements
if is_raspberry_pi:
    install_requires.extend(
        [
            "rpi_ws281x>=5.0.0",
            "adafruit-circuitpython-neopixel>=6.3.9",
        ]
    )

setup(
    name="gitlit-controller",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "black>=23.11.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
        ]
    },
    python_requires=">=3.9",
    author="GitLit Team",
    description="LED controller for Raspberry Pi",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    entry_points={
        "console_scripts": [
            "led-client=client.led_client:main",
        ],
    },
)
