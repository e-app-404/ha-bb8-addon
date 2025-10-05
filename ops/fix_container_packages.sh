#!/bin/bash
# Manual package installation script for BB8 add-on container

set -e

echo "=== BB8 Add-on Manual Package Installation ==="

# Find the container ID
CID=$(docker ps -q --filter name=addon_local_beep_boop_bb8 | head -1)

if [ -z "$CID" ]; then
    echo "❌ BB8 add-on container not found"
    exit 1
fi

echo "✅ Container ID: $CID"

# Install packages in the container
echo "📦 Installing packages in container..."
docker exec "$CID" /opt/venv/bin/pip install --no-cache-dir paho-mqtt==2.1.0 bleak==0.22.3 spherov2==0.12.1 PyYAML

# Verify installation
echo "🔍 Verifying paho-mqtt installation..."
docker exec "$CID" /opt/venv/bin/python -c "import paho.mqtt.client as m; print('✅ paho-mqtt version:', m.__version__)"

echo "🔍 Verifying bleak installation..."
docker exec "$CID" /opt/venv/bin/python -c "import bleak; print('✅ bleak version:', bleak.__version__)"

echo "🔍 Verifying spherov2 installation..."
docker exec "$CID" /opt/venv/bin/python -c "import spherov2; print('✅ spherov2 imported successfully')"

echo "✅ All packages installed successfully!"
echo "⚠️  Note: This is a temporary fix. Packages will be lost when container restarts."
echo "🔄 Add-on will need to be restarted to pick up new packages..."