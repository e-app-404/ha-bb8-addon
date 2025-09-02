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
COPY run.sh /run.sh
COPY requirements.txt* /usr/src/app/
RUN test -x /usr/src/app/run.sh || (echo 'FATAL: run.sh missing from build context' >&2; exit 53)
RUN test -x /usr/src/app/run.sh || (echo 'FATAL: run.sh missing from build context' >&2; exit 53)

# Base deps (Debian BUILD_FROM) — Alpine is NOT supported here
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip ca-certificates bash jq --fix-missing \
  && rm -rf /var/lib/apt/lists/*

# Create venv and install deps into venv
RUN python3 -m venv "/opt/venv" \
 && /opt/venv/bin/pip install --no-cache-dir -U pip setuptools wheel \
 && if [ -f /usr/src/app/requirements.txt ]; then \
   /opt/venv/bin/pip install --no-cache-dir -r /usr/src/app/requirements.txt ; \
    fi \
 && chmod +x /usr/src/app/run.sh \
 && rm -rf /usr/src/app/tests /usr/src/app/__pycache__ /usr/src/app/.pytest_cache || true

# Ensure interactive shells see the venv first (affects docker exec bash -lc)
RUN printf '%s\n' \
    'export VIRTUAL_ENV=/opt/venv' \
    'export PATH="/opt/venv/bin:$PATH"' \
    > /etc/profile.d/venv_path.sh
  RUN chmod 0644 /etc/profile.d/venv_path.sh

# (Optional) also export venv PATH early for s6 services that don’t source profile
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
RUN echo "2025.08.21" > /usr/src/app/VERSION

# S6 Entrypoint
ENTRYPOINT [ "/init" ]
# (removed stray trailing ENV continuation; PYTHONUNBUFFERED is already set above)