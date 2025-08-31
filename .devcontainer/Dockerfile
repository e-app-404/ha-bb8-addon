# (Optional) Add-on devcontainer Dockerfile for custom provisioning
# Use the base image from Home Assistant devcontainer
FROM ghcr.io/home-assistant/devcontainer:stable

# Install any additional system dependencies for BLE, D-Bus, etc.
RUN apk add --no-cache bluez dbus glib-dev py3-paho-mqtt

# (Optional) Install Python tools globally if needed
# RUN pip install --upgrade pip

# Set up D-Bus and BLE permissions if needed
