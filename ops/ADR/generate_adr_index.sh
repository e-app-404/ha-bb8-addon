#!/usr/bin/env bash
set -uo pipefail
# Utility requirements:
# - yq (https://github.com/mikefarah/yq)
# - awk, grep, sed, sort (GNU versions recommended)
# - bash (v4+)
#
# Install yq: brew install yq (macOS) or pip install yq (Python version)
#
ADR_DIR="$(cd "$(dirname "$0")/../../docs/ADR" && pwd)"
INDEX_FILE="$ADR_DIR/INDEX.md"
TMP_INDEX="$(mktemp)"

log() {
  echo "[INFO] $1"
}
warn() {
  echo "[WARN] $1" >&2
}

log "Starting ADR index generation. ADR directory: $ADR_DIR"

# Write header
cat <<EOF > "$TMP_INDEX"
# ADR Index

_Generated: $(date -u +%Y-%m-%dT%H:%M:%S%z)_

| ADR        | Title                                   | Status     | Date       | Author                | Related         | Supersedes         | Last Updated | Token Block | Machine Block |
|------------|-----------------------------------------|------------|------------|-----------------------|-----------------|--------------------|--------------|-------------|--------------|
EOF

# Find and sort ADR files numerically
find "$ADR_DIR" -maxdepth 1 -name 'ADR-*.md' ! -name 'ADR-template.md' | sort -V | while read -r adr; do
  log "Processing $adr"
  # Extract YAML front-matter (only lines between first and second ---)
  yaml=$(awk 'BEGIN{found=0} /^---/{if(found==0){found=1;next}else{exit}} found==1' "$adr")
  if [ -z "$yaml" ]; then
    warn "No YAML front-matter found in $adr. Skipping."
    continue
  fi
  # Write YAML to temp for yq, normalizing tabs and quoting unsafe plain scalars (values containing ': ')
  yaml_tmp=$(mktemp)
  echo "$yaml" \
    | sed -e $'s/\t/  /g' -e 's/\r$//' \
    | awk '
      # Quote any single-line scalar value that contains colon+space and is not already quoted or a flow collection.
      # Examples fixed:
      #   title: ADR-0001: Canonical Topology  ->  title: "ADR-0001: Canonical Topology"
      # Safe: does NOT touch keys with block values (e.g., "related:" followed by "- item")
      /^[[:space:]]*[A-Za-z0-9_]+:[[:space:]]*[^"'\''\[{][^#\n]*: [^#\n]*$/ {
        key = substr($0, 1, index($0, ":"))
        val = substr($0, index($0, ":") + 1)
        gsub(/^[[:space:]]+/, "", val)
        gsub(/"/, "\\\"", val)  # escape any embedded double-quotes
        print key " \"" val "\""
        next
      }
      {print}
    ' > "$yaml_tmp"
  # Extract fields using yq
  title=$(yq '.title // "-"' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse title"; echo "-"; })
  date=$(yq '.date // "-"' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse date"; echo "-"; })
  status=$(yq '.status // "-"' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse status"; echo "-"; })
  author=$(yq '.author // [] | join(", ")' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse author"; echo "-"; })
  related=$(yq '.related // [] | join(",")' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse related"; echo "-"; })
  # Highlight non-ADR references
  related=$(echo "$related" | awk -F, '{for(i=1;i<=NF;i++){if($i!~/^ADR-[0-9]{4}$/){$i="(" $i ")"};printf "%s%s", $i, (i<NF?",":"")}}')
  supersedes=$(yq '.supersedes // [] | join(",")' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse supersedes"; echo "-"; })
  last_updated=$(yq '.last_updated // "-"' "$yaml_tmp" 2>/dev/null || { warn "$adr: yq failed to parse last_updated"; echo "-"; })
  rm "$yaml_tmp"

  # Warn if any required field is missing
  for field in title date status author; do
    eval val=\$$field
    if [ "$val" = "-" ]; then warn "$adr missing field: $field"; fi
  done




  # Extract first YAML code block and both TOKEN_BLOCK and MACHINE_BLOCK from it
  token_block="-"
  machine_block="-"
  block=$(awk '/^```yaml|^```yml/{inblock=1; next} /^```/{inblock=0} inblock' "$adr")
  if [ -n "$block" ]; then
    token_block=$(echo "$block" | awk '/^TOKEN_BLOCK:/{capture=1} capture{print} END{}' | tr "\n" " " | xargs)
    [ -z "$token_block" ] && token_block="-"
    machine_block=$(echo "$block" | awk '/^MACHINE_BLOCK:/{capture=1} capture{print} END{}' | tr "\n" " " | xargs)
    [ -z "$machine_block" ] && machine_block="-"
  fi

  # Escape pipes in all values
  esc() { echo "$1" | sed 's/|/\\|/g'; }
  title=$(esc "$title")
  status=$(esc "$status")
  date=$(esc "$date")
  author=$(esc "$author")
  related=$(esc "$related")
  supersedes=$(esc "$supersedes")
  last_updated=$(esc "$last_updated")
  token_block=$(esc "$token_block")
  machine_block=$(esc "$machine_block")

  # Format ADR filename
  adr_name=$(basename "$adr")
  adr_link="[$adr_name]($adr_name)"

  # Write row
  printf "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n" \
    "$adr_link" "$title" "$status" "$date" "$author" "$related" "$supersedes" "$last_updated" "$token_block" "$machine_block" >> "$TMP_INDEX"
done

log "Moving index to $INDEX_FILE"
mv "$TMP_INDEX" "$INDEX_FILE"
log "ADR index generated at $INDEX_FILE"