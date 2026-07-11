#!/usr/bin/env bash
set -x

# Ensure we are in the application directory
cd /app || exit 1

# Activate the virtual environment
source .venv/bin/activate

# Print diagnostic info to logs
pwd
ls -F

# Start the application using the full path to the interpreter
exec /app/.venv/bin/python main.py

