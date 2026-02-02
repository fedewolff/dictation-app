#!/bin/bash
#
# Create Desktop Shortcut for Dictation App (Automator version)
#

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HOME/Desktop/Dictation.app"

echo "Creating Dictation App shortcut..."

# Remove existing
rm -rf "$APP_PATH" 2>/dev/null

# Create Automator app structure
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# Create the executable script
cat > "$APP_PATH/Contents/MacOS/Dictation" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
source venv/bin/activate
exec python3 -m src.main "\$@"
EOF
chmod +x "$APP_PATH/Contents/MacOS/Dictation"

# Create Info.plist
cat > "$APP_PATH/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Dictation</string>
    <key>CFBundleIdentifier</key>
    <string>com.local.dictation</string>
    <key>CFBundleName</key>
    <string>Dictation</string>
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
echo "Done! Dictation.app created on Desktop."
echo ""
echo "First launch: Right-click → Open → Open"
echo "After that, double-click works normally."
