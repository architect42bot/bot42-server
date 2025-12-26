#!/usr/bin/env bash
# Simple launcher for 42 on a VPS

# Change to project directory (edit this path on the VPS!)
cd /opt/bot42

# Activate virtualenv
source venv/bin/activate

# Run uvicorn
exec uvicorn main:app --host 0.0.0.0 --port 8000