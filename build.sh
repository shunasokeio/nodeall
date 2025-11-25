#!/usr/bin/env bash
# Build script for Render
set -o errexit

# Upgrade pip, setuptools, and wheel
pip install --upgrade pip setuptools wheel

# Install requirements
pip install -r requirements.txt

