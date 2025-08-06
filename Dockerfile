# Home Assistant Add-on Dockerfile for BB-8 BLE/MQTT Bridge
ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-python:3.13-alpine3.21
FROM ${BUILD_FROM}

# Home Assistant metadata labels
LABEL io.hass.arch="aarch64"
LABEL io.hass.type="addon"

# Install system dependencies for BLE
RUN apk add --no-cache bluez dbus glib-dev

# Copy add-on source
COPY run.sh /app/run.sh
COPY app/test_ble_adapter.py /app/test_ble_adapter.py
COPY services.d/ble_bridge/run /etc/services.d/ble_bridge/run
RUN chmod +x /etc/services.d/ble_bridge/run \
  && chmod +x /app/run.sh
WORKDIR /app

# Install Python dependencies
RUN apk add --no-cache py3-paho-mqtt

# S6 Entrypoint
CMD [ "/init" ]
