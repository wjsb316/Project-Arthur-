#!/bin/bash
set -e

# Ensure the current directory is in PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/app

# Start DBus (required for Avahi)
mkdir -p /var/run/dbus
if [ -f /var/run/dbus/pid ]; then
  rm /var/run/dbus/pid
fi
dbus-daemon --system --fork

# Start Avahi Daemon
avahi-daemon -D

# Start FastAPI
# Using --host 0.0.0.0 to make it accessible outside container (required for Docker networking)
# Access control is handled by FrontendAccessMiddleware
exec uvicorn ap.app:create_app --host "${ARTHUR_HOST:-0.0.0.0}" --port "${ARTHUR_PORT:-8000}" --factory
