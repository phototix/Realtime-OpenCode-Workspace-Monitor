#!/bin/bash

SRC="/Volumes/Files/Projects/Realtime-OpenCode-Workspace-Monitor/android-apk-dev/app/build/outputs/apk/debug/app-debug.apk"
DEST="/Volumes/Files/Nextcloud/WebbyPage/Documents/Projects/MyApps-Development"

if [ ! -f "$SRC" ]; then
    echo "Error: APK not found at $SRC"
    echo "Run './gradlew assembleDebug' first."
    exit 1
fi

if [ ! -d "$DEST" ]; then
    echo "Error: Destination directory not found: $DEST"
    exit 1
fi

# Remove existing MyDora APK from destination
echo "Removing old MyDora APKs..."
find "$DEST" -maxdepth 1 -name '*MyDora*debug*' -exec rm -v {} \;
find "$DEST" -maxdepth 1 -name '*realtime-monitor*debug*' -exec rm -v {} \;

# Copy new APK
ts=$(date +%s)
destFile="$DEST/${ts}_MyDora-debug.apk"
echo "Copying to $destFile ..."

cp "$SRC" "$destFile"
if [ $? -eq 0 ]; then
    echo "Done: ${ts}_MyDora-debug.apk deployed"
else
    echo "cp failed, trying Finder fallback..."
    osascript -e "
        tell application \"Finder\"
            set srcFile to POSIX file \"$SRC\" as alias
            set destFolder to POSIX file \"$DEST\" as alias
            set newFile to duplicate file srcFile to destFolder with replacing
            set name of newFile to \"${ts}_MyDora-debug.apk\"
        end tell
    " 2>/dev/null && echo "Done: ${ts}_MyDora-debug.apk deployed"
fi

# Copy to dashboard public folder for download
DASHBOARD_PUBLIC="$HOME/.opencode-dashboard"
cp "$SRC" "$DASHBOARD_PUBLIC/mydora-latest.apk"
echo "Also saved to $DASHBOARD_PUBLIC/mydora-latest.apk"
