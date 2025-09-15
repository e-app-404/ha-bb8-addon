#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# --- Defaults ---
EXCLUDES_DEFAULT=".git .venv _backups _bundles reports __pycache__ .pytest_cache .mypy_cache node_modules *.pyc *.pyo .DS_Store"
EXCLUDES="${EXCLUDES:-$EXCLUDES_DEFAULT}"
TARBALL_DIR="${TARBALL_DIR:-_backups}"
INVENTORY_DIR="${INVENTORY_DIR:-${TARBALL_DIR}/inventory}"
TS="$(date +%Y%m%d_%H%M%S)"
BASE="wtree_full_${TS}"
NAME="${BASE}"
OUT_DIR="${OUT_DIR:-$TARBALL_DIR}"
ZSTD=0
DRY_RUN=0
VERIFY=0
INCLUDE_UNTRACKED=0
ALL=0
GIT=0
TARBALL=""

# --- CLI Parsing ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tracked-only) INCLUDE_UNTRACKED=0 ;;
        --include-untracked) INCLUDE_UNTRACKED=1 ;;
        --all) ALL=1 ;;
        --out-dir) OUT_DIR="$2"; shift ;;
        --name) NAME="$2"; shift ;;
        --zstd) ZSTD=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --verify) VERIFY=1; TARBALL="$2"; shift ;;
        *) echo "Unknown flag: $1" >&2; exit 2 ;;
    esac
    shift
done

# --- Detect tools ---
GTAR_BIN="$(command -v gtar || command -v tar)"
ZSTD_BIN="$(command -v zstd || true)"
SHA256_BIN="$(command -v sha256sum || command -v shasum)"
if [[ "$SHA256_BIN" == *shasum ]]; then SHA256_BIN="$SHA256_BIN -a 256"; fi

# --- Git detection ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT=1
    GIT_COMMIT="$(git rev-parse HEAD)"
    GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
    GIT_DIRTY="$(git status --porcelain | grep . && echo 1 || echo 0)"
else
    GIT=0
    GIT_COMMIT=""
    GIT_BRANCH=""
    GIT_DIRTY=""
fi

# --- Output paths ---
mkdir -p "$OUT_DIR" "$INVENTORY_DIR"
TARBALL_EXT="tgz"
if [[ $ZSTD -eq 1 && -n "$ZSTD_BIN" ]]; then TARBALL_EXT="tar.zst"; fi
TARBALL_PATH="$OUT_DIR/${NAME}.${TARBALL_EXT}"
MANIFEST_PATH="$INVENTORY_DIR/manifest_${TS}.txt"
TREE_PATH="$INVENTORY_DIR/tree_${TS}.txt"
META_PATH="$INVENTORY_DIR/meta_${TS}.json"
SHA256_PATH="$OUT_DIR/${NAME}.sha256"

# --- File list ---
ROOTS=(addon docs ops Makefile .coveragerc .gitignore .githooks .github)
INCLUDE=()
for root in "${ROOTS[@]}"; do
    [[ -e "$root" ]] && INCLUDE+=("$root")
done

# --- Exclude expansion for find ---
FIND_EXCLUDES=()
for ex in $EXCLUDES; do
    FIND_EXCLUDES+=( -not -path "*/$ex*" )
done

# --- Gather files ---
if [[ $ALL -eq 1 || $GIT -eq 0 ]]; then
    FILES=( $(find "${INCLUDE[@]}" -type f "${FIND_EXCLUDES[@]}" | sort) )
else
    if [[ $INCLUDE_UNTRACKED -eq 1 ]]; then
        FILES=( $(git ls-files --cached --others --exclude-standard ${INCLUDE[@]}) )
    else
        FILES=( $(git ls-files --cached ${INCLUDE[@]}) )
    fi
fi
COUNT=${#FILES[@]}

# --- Dry run ---
if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY RUN] Would include $COUNT files:"
    printf '%s\n' "${FILES[@]}"
    echo "TOKEN:COUNT=$COUNT"
    exit 0
fi

# --- Manifest ---
: > "$MANIFEST_PATH"
for f in "${FILES[@]}"; do
    sz=$(stat -f %z "$f" 2>/dev/null || stat -c %s "$f")
    mt=$(stat -f %m "$f" 2>/dev/null || stat -c %Y "$f")
    sha=$($SHA256_BIN "$f" | awk '{print $1}')
    echo "$f|$sz|$mt|$sha" >> "$MANIFEST_PATH"
done

# --- Tree ---
find "${INCLUDE[@]}" -type f "${FIND_EXCLUDES[@]}" | sort > "$TREE_PATH"

# --- Metadata ---
cat > "$META_PATH" <<EOF
{
  "timestamp": "$TS",
  "file_count": $COUNT,
  "tarball": "$TARBALL_PATH",
  "manifest": "$MANIFEST_PATH",
  "tree": "$TREE_PATH",
  "meta": "$META_PATH",
  "sha256": "$SHA256_PATH",
  "git": {
    "enabled": $GIT,
    "commit": "$GIT_COMMIT",
    "branch": "$GIT_BRANCH",
    "dirty": "$GIT_DIRTY"
  }
}
EOF

# --- Tarball creation ---
if [[ $ZSTD -eq 1 && -n "$ZSTD_BIN" ]]; then
    TAR_CMD=("$GTAR_BIN" --sort=name --owner=0 --group=0 --mtime="@$TS" -cf - "${FILES[@]}")
    "${TAR_CMD[@]}" | "$ZSTD_BIN" -q -o "$TARBALL_PATH"
else
    if [[ "$GTAR_BIN" == *gtar ]]; then
        "$GTAR_BIN" --sort=name --owner=0 --group=0 --mtime="@$TS" -czf "$TARBALL_PATH" "${FILES[@]}"
    else
        "$GTAR_BIN" -czf "$TARBALL_PATH" "${FILES[@]}"
    fi
fi

# --- Tarball SHA256 ---
$SHA256_BIN "$TARBALL_PATH" | awk '{print $1}' > "$SHA256_PATH"
TARBALL_SHA=$(cat "$SHA256_PATH")

# --- Output tokens ---
echo "TOKEN:TARBALL=$TARBALL_PATH"
echo "TOKEN:MANIFEST=$MANIFEST_PATH"
echo "TOKEN:SHA256=$TARBALL_SHA"
echo "TOKEN:COUNT=$COUNT"

# --- Verify mode ---
if [[ $VERIFY -eq 1 ]]; then
    if [[ ! -f "$TARBALL" ]]; then
        echo "Tarball not found: $TARBALL" >&2; exit 3
    fi
    TARBALL_SHA2=$($SHA256_BIN "$TARBALL" | awk '{print $1}')
    SHA_FILE="${TARBALL%.*}.sha256"
    if [[ -f "$SHA_FILE" ]]; then
        SHA_EXPECT=$(cat "$SHA_FILE")
        if [[ "$TARBALL_SHA2" != "$SHA_EXPECT" ]]; then
            echo "SHA256 mismatch: $TARBALL_SHA2 != $SHA_EXPECT" >&2; exit 4
        fi
    fi
    echo "Verified tarball: $TARBALL"
    exit 0
fi

exit 0
