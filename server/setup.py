from setuptools import setup, find_packages

setup(
    name="gitlit-server",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "numpy>=1.24.0",
        "librosa>=0.10.1",
        "essentia>=2.1b6.dev1034",
        "websockets>=11.0.3",
        "pydantic>=2.5.2",
        "python-multipart>=0.0.6",
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
    description="Audio reactive LED pattern server",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
