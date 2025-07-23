#!/usr/bin/env python3

from pathlib import Path
from setuptools import find_packages, setup

with Path("README.md").open() as fh:
    long_description = fh.read()

setup(
    name="sbm",
    version="2.0.0",
    author="Nathan Hart",
    author_email="nhart@dealerinspire.com",
    description="Site Builder Migration Tool - Automate dealer website migrations to the Site Builder platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nate-hart-di/auto-sbm",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "sbm=sbm.cli:cli",
        ],
    },
)
