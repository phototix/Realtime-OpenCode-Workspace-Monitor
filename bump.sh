#!/usr/bin/env bash
set -e

VERSION_FILE="$(dirname "$0")/version.txt"
INDEX_FILE="$(dirname "$0")/index.html"

OLD_VER=$(cat "$VERSION_FILE")
NEW_VER=$((OLD_VER + 1))

sed -i '' "s/\\?v=$OLD_VER/?v=$NEW_VER/g" "$INDEX_FILE"
echo "$NEW_VER" > "$VERSION_FILE"

echo "Bumped v$OLD_VER -> v$NEW_VER (index.html + version.txt)"
