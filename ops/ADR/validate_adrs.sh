#!/usr/bin/env bash
set -euo pipefail

command -v yq >/dev/null 2>&1 || { echo "yq is required but not installed. Aborting." >&2; exit 1; }

ADR_DIR="${1:-docs/ADR}"

fail() { echo "::error file=$1,line=${2:-0}::$3" >&2; exit 1; }

shopt -s nullglob
for file in "$ADR_DIR"/ADR-*.md; do
 # Extract front-matter
 fm="$(awk '/^---/{flag=!flag; next} flag' "$file" | sed $'s/\t/ /g' | tr -d '\r')"
 [ -z "$fm" ] && fail "$file" 1 "Missing YAML front-matter."

 tmp="$(mktemp)"
 # Quote unsafe single-line scalars with colon+space (defensive), preserve inline comments
 echo "$fm" | awk '
 match($0, /^[[:space:]]*([A-Za-z0-9_.-]+):[[:space:]]*(.*)$/, m) {
 key=m[1]; val=m[2];
 if (val ~ /^$/) { print; next }
 if (val ~ /^['"\[{>|!&*]/) { print; next }
 # separate inline comment (starts with space + #)
 cidx = index(val, " #")
 if (cidx>0) { v=substr(val,1,cidx-1); comment=substr(val,cidx) } else { v=val; comment="" }
 # trim
 sub(/^[[:space:]]+/, "", v); sub(/[[:space:]]+$/, "", v)
 if (v ~ /: / || v ~ /(^[ \t]|[ \t]$)/) {
 gsub(/"/, "\\\"", v);
 indent = substr($0, 1, index($0, key)-1)
 print indent key ": \"" v "\"" comment
 next
 }
 print; next
 }
 { print }
 # Basic shape checks with yq
 yq -e '.title and .date and .status and (.author|length>0) and (.related != null) and (.supersedes != null) and .last_updated' "$tmp" >/dev/null \
 || fail "$file" 1 "Front-matter missing required keys."
 yq -e '.title and .date and .status and (.author|length>0) and (.related) and (.supersedes) and .last_updated' "$tmp" >/dev/null \
 || fail "$file" 1 "Front-matter missing required keys."

 # Status normalization (treat Approved as Accepted)
 status="$(yq -r '.status' "$tmp")"
 case "$status" in
 Draft|Proposed|Accepted|Amended|Deprecated|Superseded|Rejected|Withdrawn) ;;
 Approved) echo "::warning file=$file::status 'Approved' is legacy; prefer 'Accepted'." ;;
 *) fail "$file" 1 "Invalid status: $status" ;;
 esac

 # Filename vs ID vs title consistency
 base="$(basename "$file")"
 [[ "$base" =~ ^ADR-([0-9]{4})-([a-z0-9-]+)\.md$ ]] || fail "$file" 1 "Filename must match ADR-XXXX-<slug>.md"
 id="${BASH_REMATCH[1]}"
title_id="$(yq -r '.title' "$tmp" | grep -o '^ADR-[0-9]\{4\}' || true)"
[ -n "$title_id" ] || fail "$file" 1 "Title must start with ADR-XXXX:"
title_id_num="${title_id#ADR-}"
[ "$id" = "$title_id_num" ] || fail "$file" 1 "ID mismatch: filename ADR-$id vs title $title_id"

 # Related/supersedes patterns
 yq -r '.related[]? // empty' "$tmp" | grep -Ev '^ADR-[0-9]{4}$' >/dev/null && fail "$file" 1 "related contains non-ADR IDs"
 yq -r '.supersedes[]? // empty' "$tmp" | grep -Ev '^ADR-[0-9]{4}$' >/dev/null && fail "$file" 1 "supersedes contains non-ADR IDs"

 # Token block presence for governance/policy ADRs (title H1)
 if grep -qiE '^(# .*\b(governance|decision|policy)\b)' "$file"; then
 awk 'tolower($0) ~ /^```(yaml|yml)/{in=1;next} /^```/{if(in){in=0}} in{print}' "$file" \
 | grep -q '^TOKEN_BLOCK:' || fail "$file" 1 "Missing TOKEN_BLOCK for governance ADR."
 fi
 done
 echo "ADR validation OK."
