#!/bin/bash
#
# Create Desktop Shortcut for Dictation Control Panel
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HOME/Desktop/Dictation Controls.app"

echo "Creating Dictation Controls shortcut..."

# Remove existing
rm -rf "$APP_PATH" 2>/dev/null

# Create app structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Create the executable script
cat > "$APP_PATH/Contents/MacOS/DictationControls" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source venv/bin/activate
exec python3 -m src.main --control-panel "\$@"
EOF
chmod +x "$APP_PATH/Contents/MacOS/DictationControls"

# Create Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>DictationControls</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.dictation-controls</string>
    <key>CFBundleName</key>
    <string>Dictation Controls</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Dictation needs microphone access for speech recognition.</string>
</dict>
</plist>
EOF

# Remove quarantine attribute
xattr -cr "$APP_PATH" 2>/dev/null

echo ""
echo "Done! 'Dictation Controls.app' created on Desktop."
echo ""
echo "This shortcut opens the Dictation app with the control panel visible."
echo ""
echo "First launch: Right-click -> Open -> Open"
echo "After that, double-click works normally."
