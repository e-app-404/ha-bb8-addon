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

  # Extract frontmatter and rest
  awk -v today="$TODAY" '
    BEGIN{state=0; related=0; supersedes=0; last_updated=0; dateval=""}
    { if(state==0){ if($0=="---"){ state=1; print $0; next } else { print $0; next } }
      else if(state==1){ if($0=="---"){ # closing frontmatter
            if(!related) print "related: []"
            if(!supersedes) print "supersedes: []"
            if(!last_updated){ if(dateval!="") print "last_updated: " dateval; else print "last_updated: " today }
            print $0; state=2; next
        }
        # inside frontmatter
        if($0 ~ /^related:\s*/){ related=1 }
        if($0 ~ /^supersedes:\s*/){ supersedes=1 }
        if($0 ~ /^last_updated:\s*/){ last_updated=1 }
        if($0 ~ /^date:\s*/){ match($0, /date:\s*(\S+)/, a); if(a[1]!="") dateval=a[1] }
        print $0; next }
      else { print $0 }
    }
  ' "$bak" > "$f.tmp"

  # Replace /Volumes/HA or /Volumes/ha with /n/ha in the whole file
  sed -e 's#/Volumes/HA#/n/ha#g' -e 's#/Volumes/ha#/n/ha#g' "$f.tmp" > "$f"
  rm -f "$f.tmp"

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
  awk 'BEGIN{in=0; fm=""} { if($0=="---" && in==0){ in=1; next } else if($0=="---" && in==1){ in=2; exit } if(in==1) fm=fm $0 "\n" } END{ print fm }' "$f" > /tmp/fm.txt
  miss=0
  for key in title date status author related supersedes last_updated; do
    if ! grep -qE "^\s*${key}:" /tmp/fm.txt; then
      echo "MISSING in $(basename "$f"): $key"
      miss=1
    fi
  done
  if [ $miss -eq 0 ]; then
    echo "OK: $(basename "$f")"
  fi
done

exit 0
