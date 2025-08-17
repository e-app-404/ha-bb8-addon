
# Home Assistant Add-on Dockerfile for BB-8 BLE/MQTT Bridge

ARG BUILD_FROM
FROM $BUILD_FROM

# Home Assistant metadata labels
LABEL io.hass.arch="aarch64"
LABEL io.hass.type="addon"

# Install system dependencies for BLE
RUN apk add --no-cache bluez dbus glib-dev

# --- TEMP: MQTT CLI tools for broker/credential testing ---
RUN apk add --no-cache mosquitto-clients


# --- App files ---
COPY run.sh /app/run.sh
COPY services.d/ble_bridge/run /etc/services.d/ble_bridge/run
COPY app/test_ble_adapter.py /app/test_ble_adapter.py
COPY bb8_core /app/bb8_core
COPY requirements.in /app/requirements.in
COPY requirements.txt /app/requirements.txt

RUN chmod +x /etc/services.d/ble_bridge/run && chmod +x /app/run.sh

WORKDIR /app
ENV PYTHONPATH=/app



# System pip (only to make sure ensurepip/venv behaves nicely)
RUN apk add --no-cache py3-pip

# ✅ Create an isolated virtualenv and install deps there
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# venv + wheels; installs go into /opt/venv and will not trigger PEP 668
RUN python3 -m venv "$VIRTUAL_ENV" \
  && python3 -m pip install --upgrade pip setuptools wheel \
  && python3 -m pip install -r /app/requirements.txt

# Build-time version injection
ARG BUILD_VERSION
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ADDON_VERSION=${BUILD_VERSION}
RUN echo "2025.08.19" > /app/VERSION

# S6 Entrypoint
ENTRYPOINT [ "/init" ]
