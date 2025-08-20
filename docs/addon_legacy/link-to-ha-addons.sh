#!/bin/bash

# not needed in the add-on anymore as folder name has been updated to match slug
# Adjust these to your local environment
REPO_DIR=$(pwd)
HA_ADDONS_DIR="/Volumes/addons"

TARGET_SLUG="beep_boop_bb8"
TARGET_DIR="$HA_ADDONS_DIR/$TARGET_SLUG"

echo "Linking $REPO_DIR to Home Assistant add-on path $TARGET_DIR..."

# Remove old link/folder if needed
if [ -L "$TARGET_DIR" ] || [ -d "$TARGET_DIR" ]; then
    echo "Removing old add-on path: $TARGET_DIR"
    rm -rf "$TARGET_DIR"
fi

ln -s "$REPO_DIR" "$TARGET_DIR"
echo "Link created: $TARGET_DIR → $REPO_DIR"

# Optional: show confirmation
ls -l "$TARGET_DIR"
