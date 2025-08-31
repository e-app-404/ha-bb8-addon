#!/usr/bin/env bash
# Bumps add-on version across files, updates changelog.
# Usage:
#   ops/release/bump_version.sh patch
#   ops/release/bump_version.sh minor
#   ops/release/bump_version.sh major
#   ops/release/bump_version.sh 1.2.3   # explicit version

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

CFG="addon/config.yaml"
DF="addon/Dockerfile"
CH="addon/CHANGELOG.md"

[ -f "$CFG" ] || { echo "ERROR: $CFG not found"; exit 2; }

# Current version from config.yaml (simple parse; expects a 'version: x.y.z' line)
CUR="$(awk -F': *' '/^version:/ {print $2; exit}' "$CFG")"
[[ "$CUR" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: bad current version '$CUR'"; exit 3; }

bump_semver() {
  local v="$1" kind="$2"
  IFS=. read -r MA MI PA <<< "$v"
  case "$kind" in
    patch) PA=$((PA+1));;
    minor) MI=$((MI+1)); PA=0;;
    major) MA=$((MA+1)); MI=0; PA=0;;
    *) echo "$kind"; return 0;;
  esac
  echo "${MA}.${MI}.${PA}"
}

REQ="${1:-patch}"
if [[ "$REQ" =~ ^(patch|minor|major)$ ]]; then
  NEW="$(bump_semver "$CUR" "$REQ")"
else
  NEW="$REQ"
fi
[[ "$NEW" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "ERROR: target version '$NEW' invalid"; exit 4; }

# 1) Update config.yaml: version: NEW
perl -0777 -pe "s/^version:\s*.*/version: ${NEW}/m" -i "$CFG"

# 2) Update Dockerfile if it exposes a version (LABEL/ARG/ENV). Apply all matches if present.
if [ -f "$DF" ]; then
  perl -0777 -pe 's/^(LABEL\s+version\s*=\s*")[^"]*(")/${1}'"$NEW"'${2}/m' -i "$DF" || true
  perl -0777 -pe 's/^(ARG\s+ADDON_VERSION\s*=\s*)\S+/\1'"$NEW"'/m' -i "$DF" || true
  perl -0777 -pe 's/^(ENV\s+ADDON_VERSION\s+)\S+/\1'"$NEW"'/m' -i "$DF" || true
fi

# 3) Changelog append
mkdir -p "$(dirname "$CH")"; touch "$CH"
TODAY="$(date +%Y-%m-%d)"
cat >> "$CH" <<EOF

## ${TODAY} — ${NEW}
- bump: add-on version to ${NEW}
- chore: synchronized config.yaml and Dockerfile
EOF

git add "$CFG" "$DF" "$CH" 2>/dev/null || true
git commit -m "release: bump add-on version to ${NEW}" || true
echo "BUMP_OK:${NEW}"
