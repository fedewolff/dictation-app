#!/bin/bash
#
# Create Desktop Shortcut for Dictation Control Panel
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HOME/Desktop/Dictation Controls.app"
PYTHON_PATH="$SCRIPT_DIR/venv/bin/python3"

echo "Creating Dictation Controls shortcut..."

# Remove existing
rm -rf "$APP_PATH" 2>/dev/null

# Create Automator-style app using osacompile
osacompile -o "$APP_PATH" << APPLESCRIPT
on run
    do shell script "pkill -9 -f 'python.*src.main' 2>/dev/null || true"
    delay 0.3
    do shell script "cd '$SCRIPT_DIR' && '$PYTHON_PATH' -m src.main --control-panel &> /dev/null &"
end run
APPLESCRIPT

# Update Info.plist
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Dictation needs microphone access'" "$APP_PATH/Contents/Info.plist" 2>/dev/null

# Remove quarantine
xattr -cr "$APP_PATH" 2>/dev/null

echo ""
echo "Done! 'Dictation Controls.app' created on Desktop."
echo ""
echo "IMPORTANT: Add this app to Accessibility permissions in System Settings."
