#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="multi-channel-rpi-eco-monitoring",
    version="1.1.0",
    author="Rifqi Ikhwanuddin",
    author_email="rifqi@ikhwanuddin.com",
    description="Multi-channel Raspberry Pi ecosystem monitoring system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.6",
    install_requires=[
        "psutil",
    ],
    entry_points={
        "console_scripts": [
            "eco-monitor-setup=setup_config:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
