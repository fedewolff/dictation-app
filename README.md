# Dictation App

A macOS dictation app that lets you speak instead of type. Press a hotkey, talk, and get your text — either as a polished message or exact transcription.

Works in **English** and **Spanish** with automatic language detection.

## What It Does

**Two modes:**

### 1. Drafting Mode
Speak your intent and AI transforms it into a professional message.

> **You say:** "tell sarah the meeting tomorrow is moved to thursday at 3"
>
> **It drafts:** "Hi Sarah, I wanted to let you know that tomorrow's meeting has been rescheduled to Thursday at 3 PM. Let me know if that works for you."

### 2. Transcription Mode
Pure speech-to-text — writes exactly what you say.

> **You say:** "remember to buy milk and eggs"
>
> **It writes:** "Remember to buy milk and eggs."

## When to Use Each Mode

| Mode | Best For |
|------|----------|
| **Drafting** | Slack messages, emails, quick replies — when you want polish without effort |
| **Transcription** | Brainstorming with ChatGPT, taking notes, journaling — when you want your exact words |

**Pro tip:** Transcription mode is great for long ChatGPT prompts. Speaking is way more fluent than typing and you can give much more context.

## Requirements

- macOS 12.0 or later
- Python 3.10+
- [Ollama](https://ollama.com/) (for drafting mode)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/fedewolff/dictation-app.git
cd dictation-app
```

### 2. Create virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Ollama and the AI model (for drafting mode)

```bash
# Install Ollama from https://ollama.com/download

# Start Ollama server (keep this running)
ollama serve

# In a new terminal, pull the model (runs 100% locally, no login needed)
ollama pull glm4:latest
```

### 4. Create desktop shortcuts

**IMPORTANT: Run these commands from Terminal (don't double-click the .sh files):**

```bash
cd ~/Desktop/dictation-app
./create_shortcut.sh              # Main app (runs in menu bar)
./create_control_panel_shortcut.sh  # Control panel for settings
```

### 5. Grant permissions (IMPORTANT!)

The app needs permissions to work. **This is the most common reason the hotkey doesn't work.**

#### Add your Python interpreter to Accessibility (REQUIRED for hotkeys):

The hotkey system uses `pynput` which requires the **Python interpreter itself** to have Accessibility permissions. This is the most important step!

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button
3. Press `Cmd+Shift+G` to open "Go to folder"
4. Find your Python path by running this in Terminal:
   ```bash
   cd ~/Desktop/dictation-app
   ls -la venv/bin/python3
   ```
   This will show something like: `venv/bin/python3 -> /path/to/python3`
5. Add the **target path** (the path after the arrow) to Accessibility
   - Common paths:
     - Homebrew: `/opt/homebrew/bin/python3` or `/usr/local/bin/python3`
     - Miniconda/Anaconda: `/Users/YOUR_USERNAME/miniconda3/bin/python3.13`
     - System: `/usr/bin/python3`
6. If your Python has a `.app` bundle (common with conda), also add it:
   - Miniconda: `/Users/YOUR_USERNAME/miniconda3/python.app`
7. Make sure the toggle is **ON**

#### Add Terminal.app to Accessibility:

1. In the same Accessibility settings, click **+**
2. Press `Cmd+Shift+G` and type: `/Applications/Utilities/Terminal.app`
3. Click **Open**
4. Make sure the toggle is **ON**

#### Add the Dictation apps to Accessibility:

1. Click **+** again
2. Navigate to your Desktop and add `Dictation.app`
3. Also add `Dictation Controls.app`
4. Make sure both toggles are **ON**

#### Grant Microphone access:

macOS will prompt you on first recording. Click **Allow**.

### 6. Make sure Ollama is running

```bash
ollama serve
```

Keep this running in the background, or Ollama will start automatically if installed via the macOS app.

## Usage

### Starting the App

**Option 1:** Double-click `Dictation Controls.app` on your Desktop (shows settings panel)

**Option 2:** Double-click `Dictation.app` on your Desktop (runs in menu bar only)

**Option 3:** From terminal:
```bash
cd ~/Desktop/dictation-app
source venv/bin/activate
python3 -m src.main --control-panel
```

### Recording

1. Press `Cmd+Shift+Space` to start recording
2. Speak your message
3. Press `Enter` to stop
4. Text is copied to your clipboard — just paste it anywhere with `Cmd+V`

### Switching Modes

Use the **menu bar icon** or **Dictation Controls** app to switch between:
- **Drafting** — AI-enhanced messages
- **Transcription** — Exact speech-to-text

## Configuration

### Using Dictation Controls (Recommended)

Open `Dictation Controls.app` to change settings directly from the UI:

| Setting | Options | Description |
|---------|---------|-------------|
| **Mode** | Drafting, Transcription | AI-enhanced vs exact speech-to-text |
| **Language** | Auto-detect, English, Spanish | Language for transcription |
| **Whisper Model** | tiny, base, small, medium, large-v3 | Larger = more accurate but slower |
| **AI Model** | glm4:latest, llama3.2:latest, llama3.1:8b, mistral:latest, qwen2.5:7b | Model for drafting mode |
| **Start Key** | cmd+shift+space (default) | Hotkey to start recording |
| **Stop Key** | enter (default) | Key to stop recording |

**Note:** Restart the app after changing hotkeys.

### Manual Configuration

You can also edit `config.yaml` directly:

```yaml
behavior:
  hotkey: "cmd+shift+space"
  stop_key: "enter"

model:
  name: "large-v3"  # Options: tiny, base, small, medium, large-v3
  language: "auto"  # Options: auto, en, es

generation:
  enabled: true
  provider: "ollama"
  model: "glm4:latest"
```

## Troubleshooting

### Nothing happens when I double-click the app

**Most common cause: Missing permissions.**

1. Make sure **Terminal.app** has Accessibility permission
2. Make sure the **Dictation app** has Accessibility permission
3. Run this in Terminal to remove quarantine:
   ```bash
   xattr -cr ~/Desktop/Dictation.app
   xattr -cr ~/Desktop/"Dictation Controls.app"
   ```

### How to add Terminal.app to Accessibility

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+**
3. Press `Cmd+Shift+G` and type: `/Applications/Utilities/Terminal.app`
4. Click **Open**

### App seems stuck or won't restart

Kill the app and try again:
```bash
pkill -f "src.main"
```

### Hotkey not working

This is usually a permissions issue. The hotkey uses `pynput` which requires specific Accessibility permissions.

**Step 1: Add the Python interpreter to Accessibility**

This is the most common fix. Find your Python path:
```bash
cd ~/Desktop/dictation-app
ls -la venv/bin/python3
```

Then add that path to **System Settings → Privacy & Security → Accessibility**.

For example, if the output shows:
```
venv/bin/python3 -> /Users/you/miniconda3/bin/python3
```

Add `/Users/you/miniconda3/bin/python3` (or `python3.13` if that's the actual binary) to Accessibility.

If you're using conda/miniconda, also add the python.app bundle:
```
/Users/YOUR_USERNAME/miniconda3/python.app
```

**Step 2: Also add these to Accessibility:**
- `/Applications/Utilities/Terminal.app`
- `~/Desktop/Dictation.app`
- `~/Desktop/Dictation Controls.app`

**Step 3: Check for conflicts**
- Open **System Settings → Keyboard → Keyboard Shortcuts → Input Sources**
- Make sure `Cmd+Shift+Space` isn't assigned to "Select the previous input source"
- If it is, disable it or change it to a different shortcut

**Step 4: Restart the app**
```bash
pkill -f "src.main"
# Then relaunch the app
```

### Text not appearing

- Make sure you pressed `Enter` to stop recording
- Check that text was copied (try `Cmd+V` to paste)

### Drafting mode not working

- Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Should show `glm4:latest`
- If not, run: `ollama pull glm4:latest`

### App starts but no window appears

- The app runs in the **menu bar** (top right of screen)
- Look for "Dictation" text in your menu bar
- Or use `Dictation Controls.app` to get a visible window

### Can't double-click .sh files to run them

That's normal on macOS. Run them from Terminal instead:
```bash
cd ~/Desktop/dictation-app
./create_control_panel_shortcut.sh
```

## License

MIT
