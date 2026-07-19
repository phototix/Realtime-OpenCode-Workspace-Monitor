#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_FILE="$SCRIPT_DIR/app-version.txt"
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=~/Library/Android/sdk
export MYDORA_STORE_FILE=/Users/brandonchong/mydora-release-key.keystore
export MYDORA_STORE_PASSWORD=MyDoraPub2024!
export MYDORA_KEY_ALIAS=mydora-key
export MYDORA_KEY_PASSWORD=MyDoraPub2024!

echo "=== MyDora Monitor — Play Store Publisher ==="

# 1. Bump version
OLD_VER=$(cat "$VERSION_FILE")
BUILD_NUM=$(echo "$OLD_VER" | grep -oP 'BUILD-\K\d+')
NEW_BUILD=$((10#$BUILD_NUM + 1))
TODAY=$(date +%Y-%m-%d)
NEW_VER="version:$TODAY-BUILD-$(printf '%03d' $NEW_BUILD)"
echo "$NEW_VER" > "$VERSION_FILE"
echo "Version: $OLD_VER → $NEW_VER"

# 2. Build debug APK and deploy to dashboard
echo "=== Building debug APK ==="
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export ANDROID_HOME=~/Library/Android/sdk
cd "$SCRIPT_DIR"
./gradlew assembleDebug
bash deploy.sh

# 3. Build release AAB
echo "=== Building release AAB ==="
if [ ! -f "${MYDORA_STORE_FILE:-/dev/null}" ]; then
    echo "ERROR: Keystore not found at $MYDORA_STORE_FILE"
    echo "Set MYDORA_STORE_FILE env var or create a keystore first:"
    echo "  keytool -genkey -v -keystore ~/mydora-release-key.keystore -alias mydora-key -keyalg RSA -keysize 2048 -validity 10000"
    exit 1
fi
./gradlew bundleRelease
echo "AAB built: $SCRIPT_DIR/app/build/outputs/bundle/release/app-release.aab"

# 4. Restart server
echo "=== Restarting server ==="
kill $(lsof -ti:5500) 2>/dev/null || true
sleep 1
nohup python3 ~/.opencode-dashboard/server.py > /tmp/server.log 2>&1 &

# 5. Publish to Play Store
echo "=== Publishing to Google Play ==="
if command -v fastlane &> /dev/null; then
    fastlane production
    echo "Published version $NEW_BUILD"
else
    echo "fastlane not installed. Install it:"
    echo "  brew install fastlane"
    echo "Then upload manually: app/build/outputs/bundle/release/app-release.aab"
fi

echo "=== Done ==="
