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

# Pull the model (runs 100% locally, no login needed)
ollama pull glm4:latest

# Start Ollama server
ollama serve
```

### 4. Create desktop shortcuts

```bash
./create_shortcut.sh              # Main app (runs in menu bar)
./create_control_panel_shortcut.sh  # Control panel for settings
```

### 5. Grant permissions

The app needs permissions to work. macOS will prompt you on first run, or you can set them manually:

**System Settings → Privacy & Security:**

- **Accessibility** — Add `Dictation.app` and/or Terminal (for hotkey detection and text pasting)
- **Microphone** — Allow access when prompted

## Usage

### Starting the App

**Option 1:** Double-click `Dictation.app` on your Desktop

**Option 2:** Double-click `Dictation Controls.app` to start with the settings panel visible

**Option 3:** From terminal:
```bash
cd dictation-app
source venv/bin/activate
python3 -m src.main
```

### Recording

1. Press `Cmd+Shift+Space` to start recording
2. Speak your message
3. Press `Enter` to stop
4. Text is copied to your clipboard — just paste it anywhere

### Switching Modes

Use the **menu bar icon** or **Dictation Controls** app to switch between:
- **Drafting** — AI-enhanced messages
- **Transcription** — Exact speech-to-text

## Configuration

Edit `config.yaml` to customize:

```yaml
# Hotkey
behavior:
  hotkey: "cmd+shift+space"
  stop_key: "enter"

# Whisper model (larger = more accurate but slower)
model:
  name: "large-v3"  # Options: tiny, base, small, medium, large-v3

# AI model for drafting mode
generation:
  enabled: true
  provider: "ollama"
  model: "glm4:latest"
```

## First Time Setup (Important!)

When you first run the app, macOS may block it. Follow these steps:

### 1. Allow the app to open

**If nothing happens when you double-click:**

1. Open **System Settings → Privacy & Security**
2. Scroll down — you'll see "Dictation was blocked"
3. Click **Open Anyway**

**Or from terminal:**
```bash
xattr -cr ~/Desktop/Dictation.app
xattr -cr ~/Desktop/"Dictation Controls.app"
```

### 2. Grant Accessibility permissions

**This is required for the hotkey to work:**

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button
3. Add **both** of these:
   - `Dictation.app` from your Desktop
   - `Terminal.app` (from Applications → Utilities)
4. Make sure both toggles are **ON**

> **Note:** Terminal needs permission because the app shortcut runs through it. Without this, the app won't start from the Desktop shortcut.

### 3. Grant Microphone access

macOS will prompt you on first recording. Click **Allow**.

### 4. Make sure Ollama is running (for drafting mode)

```bash
ollama serve
```

Keep this running in the background, or Ollama will start automatically if installed via the macOS app.

## Troubleshooting

### Nothing happens when I click the app
1. Check System Settings → Privacy & Security for "blocked" message
2. Run `xattr -cr ~/Desktop/Dictation.app` in terminal
3. Try again

### Hotkey not working
- Grant Accessibility permissions (see above)
- Restart the app after granting permissions
- Make sure no other app is using `Cmd+Shift+Space`

### Text not appearing
- Make sure you pressed `Enter` to stop recording
- Check that text was copied (try `Cmd+V` to paste)

### Drafting mode not working
- Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Should show `glm4:latest`

### "Model not found" error
```bash
ollama pull glm4:latest
```

### App starts but no window appears
- The app runs in the **menu bar** (top right of screen)
- Look for "Dictation" text in your menu bar
- Or use `Dictation Controls.app` to get a visible window

## License

MIT
