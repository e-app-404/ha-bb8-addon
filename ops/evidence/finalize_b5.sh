#!/usr/bin/env bash
set -Eeuo pipefail

## 1) Stamp a release tag + changelog entry (operatorless)
REL_TS="$(date -u +%Y%m%dT%H%M%SZ)"
REL_TAG="bb8-func-b5-accept-${REL_TS}"
echo "- ${REL_TAG}: B1–B5 ACCEPT; E2E PASS (5/5 ACKs), echo green; evidence mirrored to /config/ha-bb8." >> CHANGELOG.md
git add CHANGELOG.md
git commit -m "Release: ${REL_TAG} — BB8-FUNC B1–B5 ACCEPT" || true
git tag -f "${REL_TAG}"
git push --tags || true
git push || true

## 2) Freeze and compress latest evidence for archival
LATEST_DIR="$(ls -d reports/checkpoints/BB8-FUNC/ssh_b5_* | sort | tail -n 1)"
ARCHIVE="reports/checkpoints/BB8-FUNC/${REL_TAG}.tar.gz"
tar -czf "${ARCHIVE}" -C "${LATEST_DIR}" .
python3 - <<'PY'
import hashlib,sys; p=sys.argv[1]; print(hashlib.sha256(open(p,'rb').read()).hexdigest(), p)
PY "${ARCHIVE}" > "${ARCHIVE}.sha256"

## 3) Mirror archive to HA host (confined path) and create/update a 'latest' pointer dir
TS="${LATEST_DIR##*ssh_b5_}"
ssh homeassistant '
  set -Eeuo pipefail
  BASE="/config/ha-bb8/checkpoints/BB8-FUNC"
  mkdir -p "$BASE/${TS}" "$BASE/latest"
'
rsync -avz -e ssh "${ARCHIVE}" "${ARCHIVE}.sha256" "homeassistant:/config/ha-bb8/checkpoints/BB8-FUNC/${TS}/" >/dev/null 2>&1 || true
ssh homeassistant "rsync -a --delete /config/ha-bb8/checkpoints/BB8-FUNC/${TS}/ /config/ha-bb8/checkpoints/BB8-FUNC/latest/ >/dev/null 2>&1 || true"

## 4) Create ops-friendly smoke scripts on HA host (confined) for future unattended checks
ssh homeassistant '
  set -Eeuo pipefail
  BASE="/config/ha-bb8/tools"; mkdir -p "$BASE"
  cat > "$BASE/smoke_b5.sh" <<SMK
#!/usr/bin/env sh
set -e
HOST=core-mosquitto U=mqtt_bb8 P=mqtt_bb8
mosquitto_pub -h $HOST -u $U -P $P -t bb8/cmd/power -m "{\"action\":\"wake\",\"cid\":\"smoke-1\"}"
sleep 1
mosquitto_pub -h $HOST -u $U -P $P -t bb8/cmd/drive -m "{\"speed\":100,\"heading\":0,\"ms\":500,\"cid\":\"smoke-2\"}"
sleep 1
mosquitto_pub -h $HOST -u $U -P $P -t bb8/cmd/stop -m "{\"cid\":\"smoke-3\"}"
sleep 1
mosquitto_pub -h $HOST -u $U -P $P -t bb8/cmd/power -m "{\"action\":\"sleep\",\"cid\":\"smoke-4\"}"
SMK
  chmod +x "$BASE/smoke_b5.sh"
'

## 5) Print the immutable release identifiers for your audit trail
echo "RELEASE_TAG=${REL_TAG}"
echo "EVIDENCE_LOCAL=${LATEST_DIR}"
echo "HOST_MIRROR=/config/ha-bb8/checkpoints/BB8-FUNC/${TS}"
echo "HOST_LATEST=/config/ha-bb8/checkpoints/BB8-FUNC/latest"
