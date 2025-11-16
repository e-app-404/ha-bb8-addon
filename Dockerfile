ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base-debian:bookworm
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

WORKDIR /usr/src/app
COPY bb8_core /usr/src/app/bb8_core
COPY config.yaml /usr/src/app/config.yaml
COPY run.sh /usr/src/app/run.sh
COPY requirements.txt* /usr/src/app/
RUN test -x /usr/src/app/run.sh || (echo 'FATAL: run.sh missing from build context' >&2; exit 53)
RUN test -x /usr/src/app/run.sh || (echo 'FATAL: run.sh missing from build context' >&2; exit 53)

# Base deps (Alpine base image - updated for Supervisor compatibility)
RUN apk add --no-cache \
    python3 py3-pip python3-dev build-base ca-certificates bash jq

# Create venv and install deps into venv
RUN python3 -m venv "/opt/venv" \
 && /opt/venv/bin/pip install --no-cache-dir -U pip setuptools wheel \
 && if [ -f /usr/src/app/requirements.txt ]; then \
   /opt/venv/bin/pip install --no-cache-dir -r /usr/src/app/requirements.txt ; \
    fi \
 && chmod +x /usr/src/app/run.sh \
 && rm -rf /usr/src/app/tests /usr/src/app/__pycache__ /usr/src/app/.pytest_cache || true

# HCI inspection tool (btmon) and DBus - install BlueZ + dbus
RUN if command -v apk >/dev/null 2>&1; then \
            apk add --no-cache bluez bluez-deprecated bluez-libs bluez-btmon dbus; \
        elif command -v apt-get >/dev/null 2>&1; then \
            apt-get update && apt-get install -y --no-install-recommends bluez dbus && rm -rf /var/lib/apt/lists/*; \
        else \
            echo "No package manager detected for bluez; skipping btmon"; \
        fi

# Ensure dbus-next available for Python DBus access
RUN /opt/venv/bin/pip install --no-cache-dir dbus-next

# Ensure interactive shells see the venv first (affects docker exec bash -lc)
RUN printf '%s\n' \
    'export VIRTUAL_ENV=/opt/venv' \
    'export PATH="/opt/venv/bin:$PATH"' \
    > /etc/profile.d/venv_path.sh
RUN chmod 0644 /etc/profile.d/venv_path.sh

# (Optional) also export venv PATH early for s6 services that don't source profile
# This is safe even if your service uses run.sh (which already prefers the venv).
RUN mkdir -p /etc/cont-init.d \
    && printf '%s\n' \
    '#!/usr/bin/with-contenv sh' \
    'export VIRTUAL_ENV=/opt/venv' \
    'export PATH="/opt/venv/bin:$PATH"' \
    > /etc/cont-init.d/10-venv-path \
    && chmod +x /etc/cont-init.d/10-venv-path
    # NOTE: This script is now a shell script, not execline, for Alpine/s6 compatibility.

# Build-time version injection
ARG BUILD_VERSION
ENV PYTHONDONTWRITEBYTECODE=1
ENV ADDON_VERSION=${BUILD_VERSION}
ENV PYTHONPATH="/usr/src/app:${PYTHONPATH}"
RUN echo "2025.10.4.52" > /usr/src/app/VERSION


# Wire S6 services from repo root into image
# Install s6 services for HA add-on (root-level services.d)
# Includes echo_responder/down to prevent dual supervision.
COPY services.d /etc/services.d
RUN chmod +x /etc/services.d/*/run || true

# S6 Entrypoint
ENTRYPOINT [ "/init" ]
# (removed stray trailing ENV continuation; PYTHONUNBUFFERED is already set above)
