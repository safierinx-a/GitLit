from setuptools import setup, find_packages

setup(
    name="gitlit-controller",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rpi_ws281x>=5.0.0",
        "adafruit-circuitpython-neopixel>=6.3.9",
        "numpy>=1.24.0",
        "sounddevice>=0.4.6",
        "websockets>=11.0.3",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "black>=23.11.0",
            "isort>=5.12.0",
            "mypy>=1.7.1",
        ]
    },
    python_requires=">=3.11",
    author="GitLit Team",
    description="LED controller and audio streaming client for Raspberry Pi",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
