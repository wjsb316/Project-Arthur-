#!/bin/bash
set -e

# Start DBus (required for Avahi)
mkdir -p /var/run/dbus
if [ -f /var/run/dbus/pid ]; then
  rm /var/run/dbus/pid
fi
dbus-daemon --system --fork

# Start Avahi Daemon
avahi-daemon -D

# Start FastAPI
# Using --host 0.0.0.0 to make it accessible outside container
exec uvicorn ap.app:create_app --host 0.0.0.0 --port 8000 --factory
