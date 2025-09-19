#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ADR_DIR="$ROOT/docs/ADR"
TODAY=$(date +%F)
changed=()

for f in "$ADR_DIR"/*.md; do
  [ -f "$f" ] || continue
  echo "Processing $f"
  bak="$f.autofix.bak"
  cp -p "$f" "$bak"

  # extract frontmatter block
  fm=$(perl -0777 -ne 'print $1 if /\A---\n(.*?)\n---\n/s' "$bak" || true)
  body=$(perl -0777 -ne 'print $2 if /\A---\n(.*?)\n---\n(.*)\z/s' "$bak" || true)
  if [ -z "$fm" ]; then
    echo "No front-matter in $f, skipping"
    continue
  fi
  newfm="$fm"
  # ensure related exists
  if ! echo "$fm" | grep -qE '^\s*related\s*:'; then
    newfm="$newfm\nrelated: []"
  fi
  # ensure supersedes exists
  if ! echo "$fm" | grep -qE '^\s*supersedes\s*:'; then
    newfm="$newfm\nsupersedes: []"
  fi
  # ensure last_updated exists; if not, use date if available
  if ! echo "$fm" | grep -qE '^\s*last_updated\s*:'; then
    # extract date
    datev=$(echo "$fm" | perl -ne 'print $1 and exit if /^\s*date:\s*(\d{4}-\d{2}-\d{2})/') || true
    if [ -n "$datev" ]; then
      newfm="$newfm\nlast_updated: $datev"
    else
      newfm="$newfm\nlast_updated: $TODAY"
    fi
  fi

  # canonicalize /Volumes/HA or /Volumes/ha -> /n/ha in body and frontmatter
  newbody=$(printf '%s' "$body" | sed -e 's#/Volumes/HA#/n/ha#g' -e 's#/Volumes/ha#/n/ha#g')
  newfm=$(printf '%s' "$newfm" | sed -e 's#/Volumes/HA#/n/ha#g' -e 's#/Volumes/ha#/n/ha#g')

  # Reconstruct file safely using here-doc that expands variables
  cat > "$f" <<EOF
---
${newfm}
---
${newbody}
EOF

  if ! cmp -s "$f" "$bak"; then
    changed+=("$f")
    echo "Patched $f (backup at $bak)"
  else
    echo "No change for $f"
  fi
done

if [ ${#changed[@]} -eq 0 ]; then
  echo "No ADR files changed"
  exit 0
fi

# Stage and commit
cd "$ROOT"
git add "${changed[@]}"
msg="docs(ADR): normalize front-matter (add last_updated, related/supersedes) and canonicalize /Volumes->/n/ha"
git commit -m "$msg"

echo "Committed ${#changed[@]} files:"
for x in "${changed[@]}"; do echo " - $x"; done

# Quick validation: ensure required keys now exist
echo
echo "Validating front-matter presence of required keys..."
for f in "$ADR_DIR"/*.md; do
  fm=$(perl -0777 -ne 'print $1 if /\A---\n(.*?)\n---\n/s' "$f" || true)
  miss=0
  for key in title date status author related supersedes last_updated; do
    if ! printf "%s" "$fm" | grep -qE "^\s*${key}\s*:"; then
      echo "MISSING in $(basename "$f"): $key"
      miss=1
    fi
  done
  if [ $miss -eq 0 ]; then
    echo "OK: $(basename "$f")"
  fi
done

exit 0
