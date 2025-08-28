#!/usr/bin/env bash
# Purpose: Create a single, robust continuity bundle for session rehydration.
# Usage:   bash ops/pack_continuity_bundle.sh
# Optional env:
#   SESS   = session id (e.g., SESS-8F2C7C94). If absent, auto-detect or synthesize.
#   TS     = override timestamp in UTC (YYYYMMDD_HHMMSSZ). If absent, generated.
set -euo pipefail

# --- Resolve repo root
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# --- Session id resolution (auto-detect gpt summaries, else synthesize)
if [ -z "${SESS:-}" ]; then
  if [ -d "reports/gpt_summary" ] && ls reports/gpt_summary/* >/dev/null 2>&1; then
    SESS="$(find reports/gpt_summary -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n1 | xargs -n1 basename)"
  else
    SESS="SESS-$(date -u +%Y%m%d_%H%M%SZ)"
  fi
fi

TS="${TS:-$(date -u +%Y%m%d_%H%M%SZ)}"

# --- Detect mode + version from addon/config.yaml (no yq)
CFG="addon/config.yaml"
if [ ! -f "$CFG" ]; then
  echo "FATAL: $CFG missing" >&2; exit 2
fi
VERSION="$(awk -F: '/^[[:space:]]*version:[[:space:]]*/{gsub(/[ "\t]/,"",$2); print $2; exit}' "$CFG")"
MODE="LOCAL_DEV"
# If there is an uncommented 'image:' line in config, set mode to PUBLISH
if grep -Eq '^[[:space:]]*image:[[:space:]]*[^#[:space:]]' "$CFG"; then MODE="PUBLISH"; fi

# --- Staging dirs
BUNDLE_ROOT="_bundles/CONTINUITY/${SESS}"
STAGE="${BUNDLE_ROOT}/staging"
OUT_TGZ="${BUNDLE_ROOT}/continuity_${SESS}_${VERSION}_${TS}.tar.gz"
mkdir -p "$STAGE"

# --- Copy includes (explicit, deterministic)
# Core ship subtree
rsync -a --delete \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='.ruff_cache' \
  --exclude='*.pyc' --exclude='*.pyo' --exclude='.DS_Store' \
  addon/ "${STAGE}/addon/"

# Canonical docs
mkdir -p "${STAGE}/docs/rehydration/${SESS}"
for f in \
  docs/OPERATIONS_OVERVIEW.md \
  docs/PATHS_MAP.md \
  docs/ADR/ADR-0008-end-to-end-flow.md
do
  [ -f "$f" ] && rsync -a "$f" "${STAGE}/docs/"
done

# All ADRs (machine-friendly policy backbone)
if ls docs/ADR-*.md >/dev/null 2>&1; then
  if ! rsync -a docs/ADR-*.md "${STAGE}/docs/"; then
    echo "WARNING: Failed to copy ADR markdown files to staging." >&2
  fi
fi
if ls docs/ADR/ADR-*.md >/dev/null 2>&1; then
  rsync -a docs/ADR/ADR-*.md "${STAGE}/docs/" || true
fi

# Rehydration seed (if present at the session path)
if [ -f "docs/rehydration/${SESS}/rehydration_seed.yaml" ]; then
  rsync -a "docs/rehydration/${SESS}/rehydration_seed.yaml" "${STAGE}/docs/rehydration/${SESS}/"
fi

# CI guards
mkdir -p "${STAGE}/.github/workflows"
for wf in \
  .github/workflows/repo-guards.yml \
  .github/workflows/paths-map-guard.yml
do
  [ -f "$wf" ] && rsync -a "$wf" "${STAGE}/.github/workflows/"
done

# Ops + scripts (operators rely on these for validation and rebuild)
if [ -d ops ]; then
  rsync -a --delete \
    --exclude='__pycache__' --exclude='.DS_Store' \
    ops/ "${STAGE}/ops/"
fi
[ -d scripts ] && rsync -a scripts/ "${STAGE}/scripts/"

# Root manifests & readmes (help successors rebuild coherently)
for f in build.yaml README.md CHANGELOG.md pyproject.toml requirements.txt requirements-dev.txt mypy.ini ruff.toml .flake8; do
  [ -f "$f" ] && rsync -a "$f" "${STAGE}/"
done

# Key receipts/contracts if present (best-effort)
mkdir -p "${STAGE}/reports"
for f in reports/tokens.json reports/qa_report_contract_v1.json reports/patch_bundle_contract_v1.json reports/evidence_manifest.json; do
  [ -f "$f" ] && rsync -a "$f" "${STAGE}/reports/"
done

# Session summaries if present
if [ -d "reports/gpt_summary/${SESS}" ]; then
  mkdir -p "${STAGE}/reports/gpt_summary/${SESS}"
  rsync -a "reports/gpt_summary/${SESS}/" "${STAGE}/reports/gpt_summary/${SESS}/"
fi

# --- Emit SESSION_ANCHOR.yaml (lightweight continuity anchor)
ANCHOR="${STAGE}/SESSION_ANCHOR.yaml"
{
  echo "session: ${SESS}"
  echo "timestamp_utc: ${TS}"
  echo "addon_version: ${VERSION}"
  echo "mode: ${MODE}"
  echo "rehydration_seed: docs/rehydration/${SESS}/rehydration_seed.yaml"
  echo "ops_docs: [docs/OPERATIONS_OVERVIEW.md, docs/PATHS_MAP.md, docs/ADR/ADR-0008-end-to-end-flow.md]"
  echo "ci_workflows: [.github/workflows/repo-guards.yml, .github/workflows/paths-map-guard.yml]"
  echo "contracts: [reports/tokens.json, reports/qa_report_contract_v1.json, reports/patch_bundle_contract_v1.json, reports/evidence_manifest.json]"
} > "$ANCHOR"

# --- Build per-file checksum manifest inside the bundle (bundle_index.json)
python3 - << 'PY' > "${STAGE}/bundle_index.json"
import hashlib, json, os, sys
root = sys.argv[1] if len(sys.argv) > 1 else "."
index = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        rel = os.path.relpath(p, root)
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1<<20), b""):
                h.update(chunk)
        index.append({"path": rel, "sha256": h.hexdigest(), "bytes": os.path.getsize(p)})
# Ignore errors from checksum manifest build to avoid script failure if Python fails
python3 - << 'PY' "${STAGE}" >> /dev/null || true
PY
python3 - << 'PY' "${STAGE}" >> /dev/null || true
# --- Create tarball (prefer gtar for deterministic options if available)
# Use BUNDLE_MTIME to configure tarball file timestamps for reproducibility.
# Default is 'UTC 2025-01-01' to ensure deterministic builds; override if needed.
BUNDLE_MTIME="${BUNDLE_MTIME:-UTC 2025-01-01}"

mkdir -p "${BUNDLE_ROOT}"
if command -v gtar >/dev/null 2>&1; then
  gtar --mtime="${BUNDLE_MTIME}" --sort=name --owner=0 --group=0 --numeric-owner \
       -C "${STAGE}" -czf "${OUT_TGZ}" .
else
  tar -C "${STAGE}" -czf "${OUT_TGZ}" .
fi
fi

# --- Tarball checksum
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "${OUT_TGZ}" > "${OUT_TGZ}.sha256"
else
  shasum -a 256 "${OUT_TGZ}" > "${OUT_TGZ}.sha256"
fi

# --- Gate: must-have entries
tar -tzf "${OUT_TGZ}" | grep -q '^addon/config.yaml$' || { echo "DRIFT:missing_addon_config_in_tar"; exit 5; }
tar -tzf "${OUT_TGZ}" | grep -q '^docs/OPERATIONS_OVERVIEW.md$' || { echo "DRIFT:missing_ops_overview_in_tar"; exit 6; }
tar -tzf "${OUT_TGZ}" | grep -q '^SESSION_ANCHOR.yaml$' || { echo "DRIFT:missing_session_anchor_in_tar"; exit 7; }

echo "TOKEN: TAR_OK:${OUT_TGZ}"
echo "TOKEN: SHA256_OK:${OUT_TGZ}.sha256"
echo "TOKEN: CONTINUITY_BUNDLE_OK"
