# Home Assistant Add-on Dockerfile for BB-8 BLE/MQTT Bridge
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.13-alpine3.21
FROM ${BUILD_FROM}

# Home Assistant metadata labels
LABEL io.hass.arch="aarch64"
LABEL io.hass.type="addon"

# Install system dependencies for BLE
RUN apk add --no-cache bluez dbus glib-dev

# Copy add-on source
# COPY src /app/src
# COPY requirements.txt /app/requirements.txt
COPY run.sh /app/run.sh
WORKDIR /app

# Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint
RUN chmod +x /app/run.sh
ENTRYPOINT ["/app/run.sh"]
