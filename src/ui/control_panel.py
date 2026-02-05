"""Standalone control panel window for dictation app settings."""

import threading
from datetime import datetime
from typing import Callable, List, Optional
from pathlib import Path
import yaml

try:
    from AppKit import (
        NSApplication,
        NSWindow,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskResizable,
        NSBackingStoreBuffered,
        NSView,
        NSColor,
        NSFont,
        NSMakeRect,
        NSTextField,
        NSButton,
        NSScreen,
        NSBezelStyleRounded,
        NSApp,
        NSPopUpButton,
        NSBox,
        NSBoxSeparator,
        NSScrollView,
        NSTableView,
        NSTableColumn,
        NSScrollView,
        NSTableViewStylePlain,
    )
    from Foundation import NSObject

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

# Import clipboard history
try:
    from src.system.clipboard_history import get_history, HistoryEntry
    HAS_HISTORY = True
except ImportError:
    HAS_HISTORY = False


class ControlPanelWindow:
    """Standalone control panel for dictation app settings."""

    def __init__(
        self,
        on_toggle_recording: Optional[Callable[[], None]] = None,
        on_set_context: Optional[Callable[[], None]] = None,
        on_clear_context: Optional[Callable[[], None]] = None,
        on_mode_change: Optional[Callable[[bool], None]] = None,
        on_language_change: Optional[Callable[[str], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_settings_change: Optional[Callable[[dict], None]] = None,
        generation_enabled: bool = True,
        generation_available: bool = True,
        config_path: Optional[str] = None,
    ):
        """Initialize control panel window."""
        self.on_toggle_recording = on_toggle_recording
        self.on_set_context = on_set_context
        self.on_clear_context = on_clear_context
        self.on_mode_change = on_mode_change
        self.on_language_change = on_language_change
        self.on_quit = on_quit
        self.on_settings_change = on_settings_change
        self.generation_enabled = generation_enabled
        self.generation_available = generation_available
        self.config_path = config_path or str(Path(__file__).parent.parent.parent / "config.yaml")

        self._window = None
        self._status_label = None
        self._record_button = None
        self._mode_popup = None
        self._language_popup = None
        self._context_label = None
        self._whisper_model_popup = None
        self._ai_model_popup = None
        self._hotkey_field = None
        self._stop_key_field = None
        self._state = "idle"
        self._has_context = False

        # History UI elements
        self._history_list_view = None
        self._history_buttons: List[NSButton] = []
        self._history_container = None
        self._selected_history_index = -1

        # Load current config
        self._load_config()

        if HAS_APPKIT:
            self._setup_window()

    def _load_config(self):
        """Load current configuration from file."""
        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
        except Exception:
            self._config = {}

    def _save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _setup_window(self) -> None:
        """Set up the control panel window using AppKit."""
        width = 380
        height = 750  # Increased height for history section

        # Get screen dimensions and center window
        screen = NSScreen.mainScreen()
        if screen:
            screen_frame = screen.frame()
            x = (screen_frame.size.width - width) / 2
            y = (screen_frame.size.height - height) / 2
        else:
            x, y = 300, 300

        # Create window
        rect = NSMakeRect(x, y, width, height)
        style = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
        )
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            NSBackingStoreBuffered,
            False,
        )

        # Configure window
        self._window.setTitle_("Dictation Controls")
        self._window.setReleasedWhenClosed_(False)
        self._window.setMinSize_(NSMakeRect(0, 0, 350, 600).size)

        # Create scroll view for content
        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutohidesScrollers_(True)
        scroll_view.setBorderType_(0)

        content_height = 1100  # Increased for history section
        content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, content_height))

        y_pos = content_height - 50

        # Title
        title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 30)
        )
        title.setStringValue_("Dictation App")
        title.setBezeled_(False)
        title.setDrawsBackground_(False)
        title.setEditable_(False)
        title.setSelectable_(False)
        title.setFont_(NSFont.boldSystemFontOfSize_(18))
        content_view.addSubview_(title)

        y_pos -= 30

        # Status indicator
        self._status_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        self._status_label.setStringValue_("Status: Ready")
        self._status_label.setBezeled_(False)
        self._status_label.setDrawsBackground_(False)
        self._status_label.setEditable_(False)
        self._status_label.setSelectable_(False)
        self._status_label.setFont_(NSFont.systemFontOfSize_(12))
        self._status_label.setTextColor_(NSColor.secondaryLabelColor())
        content_view.addSubview_(self._status_label)

        y_pos -= 40

        # Record button
        self._record_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 36)
        )
        self._record_button.setTitle_("Start Recording")
        self._record_button.setBezelStyle_(NSBezelStyleRounded)
        self._record_button.setTarget_(self)
        self._record_button.setAction_("toggleRecording:")
        self._record_button.setFont_(NSFont.systemFontOfSize_(14))
        content_view.addSubview_(self._record_button)

        y_pos -= 50

        # Separator
        sep1 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep1.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep1)

        y_pos -= 30

        # === SETTINGS SECTION ===
        settings_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        settings_title.setStringValue_("Settings")
        settings_title.setBezeled_(False)
        settings_title.setDrawsBackground_(False)
        settings_title.setEditable_(False)
        settings_title.setSelectable_(False)
        settings_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        content_view.addSubview_(settings_title)

        y_pos -= 35

        # Mode
        mode_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        mode_label.setStringValue_("Mode:")
        mode_label.setBezeled_(False)
        mode_label.setDrawsBackground_(False)
        mode_label.setEditable_(False)
        mode_label.setSelectable_(False)
        mode_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(mode_label)

        self._mode_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 25)
        )
        self._mode_popup.addItemWithTitle_("Drafting (AI-enhanced)")
        self._mode_popup.addItemWithTitle_("Transcription (basic)")

        if not self.generation_available:
            self._mode_popup.itemAtIndex_(0).setEnabled_(False)
            self._mode_popup.itemAtIndex_(0).setTitle_("Drafting (unavailable)")
            self._mode_popup.selectItemAtIndex_(1)
        elif not self.generation_enabled:
            self._mode_popup.selectItemAtIndex_(1)

        self._mode_popup.setTarget_(self)
        self._mode_popup.setAction_("modeChanged:")
        content_view.addSubview_(self._mode_popup)

        y_pos -= 35

        # Language
        lang_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        lang_label.setStringValue_("Language:")
        lang_label.setBezeled_(False)
        lang_label.setDrawsBackground_(False)
        lang_label.setEditable_(False)
        lang_label.setSelectable_(False)
        lang_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(lang_label)

        self._language_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 25)
        )
        self._language_popup.addItemWithTitle_("Auto-detect")
        self._language_popup.addItemWithTitle_("English only")
        self._language_popup.addItemWithTitle_("Spanish only")
        self._language_popup.setTarget_(self)
        self._language_popup.setAction_("languageChanged:")
        content_view.addSubview_(self._language_popup)

        y_pos -= 35

        # Whisper Model
        whisper_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        whisper_label.setStringValue_("Whisper Model:")
        whisper_label.setBezeled_(False)
        whisper_label.setDrawsBackground_(False)
        whisper_label.setEditable_(False)
        whisper_label.setSelectable_(False)
        whisper_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(whisper_label)

        self._whisper_model_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 25)
        )
        whisper_models = ["tiny", "base", "small", "medium", "large-v3"]
        for model in whisper_models:
            self._whisper_model_popup.addItemWithTitle_(model)

        # Set current value
        current_whisper = self._config.get("model", {}).get("name", "large-v3")
        if current_whisper in whisper_models:
            self._whisper_model_popup.selectItemWithTitle_(current_whisper)

        self._whisper_model_popup.setTarget_(self)
        self._whisper_model_popup.setAction_("whisperModelChanged:")
        content_view.addSubview_(self._whisper_model_popup)

        y_pos -= 35

        # AI Model
        ai_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        ai_label.setStringValue_("AI Model:")
        ai_label.setBezeled_(False)
        ai_label.setDrawsBackground_(False)
        ai_label.setEditable_(False)
        ai_label.setSelectable_(False)
        ai_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(ai_label)

        self._ai_model_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 25)
        )
        ai_models = ["glm4:latest", "llama3.2:latest", "llama3.1:8b", "mistral:latest", "qwen2.5:7b"]
        for model in ai_models:
            self._ai_model_popup.addItemWithTitle_(model)

        # Set current value
        current_ai = self._config.get("generation", {}).get("model", "glm4:latest")
        if current_ai in ai_models:
            self._ai_model_popup.selectItemWithTitle_(current_ai)
        else:
            self._ai_model_popup.addItemWithTitle_(current_ai)
            self._ai_model_popup.selectItemWithTitle_(current_ai)

        self._ai_model_popup.setTarget_(self)
        self._ai_model_popup.setAction_("aiModelChanged:")
        content_view.addSubview_(self._ai_model_popup)

        y_pos -= 40

        # Separator
        sep2 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep2.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep2)

        y_pos -= 30

        # === HOTKEYS SECTION ===
        hotkey_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        hotkey_title.setStringValue_("Hotkeys")
        hotkey_title.setBezeled_(False)
        hotkey_title.setDrawsBackground_(False)
        hotkey_title.setEditable_(False)
        hotkey_title.setSelectable_(False)
        hotkey_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        content_view.addSubview_(hotkey_title)

        y_pos -= 35

        # Start Recording Hotkey
        hotkey_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        hotkey_label.setStringValue_("Start Key:")
        hotkey_label.setBezeled_(False)
        hotkey_label.setDrawsBackground_(False)
        hotkey_label.setEditable_(False)
        hotkey_label.setSelectable_(False)
        hotkey_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(hotkey_label)

        self._hotkey_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 24)
        )
        current_hotkey = self._config.get("behavior", {}).get("hotkey", "cmd+shift+space")
        self._hotkey_field.setStringValue_(current_hotkey)
        self._hotkey_field.setFont_(NSFont.systemFontOfSize_(12))
        self._hotkey_field.setTarget_(self)
        self._hotkey_field.setAction_("hotkeyChanged:")
        content_view.addSubview_(self._hotkey_field)

        y_pos -= 35

        # Stop Recording Key
        stop_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 20)
        )
        stop_label.setStringValue_("Stop Key:")
        stop_label.setBezeled_(False)
        stop_label.setDrawsBackground_(False)
        stop_label.setEditable_(False)
        stop_label.setSelectable_(False)
        stop_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(stop_label)

        self._stop_key_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(130, y_pos - 2, width - 150, 24)
        )
        current_stop = self._config.get("behavior", {}).get("stop_key", "enter")
        self._stop_key_field.setStringValue_(current_stop)
        self._stop_key_field.setFont_(NSFont.systemFontOfSize_(12))
        self._stop_key_field.setTarget_(self)
        self._stop_key_field.setAction_("stopKeyChanged:")
        content_view.addSubview_(self._stop_key_field)

        y_pos -= 30

        # Note about restart
        restart_note = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 30)
        )
        restart_note.setStringValue_("Note: Restart app for hotkey changes to take effect")
        restart_note.setBezeled_(False)
        restart_note.setDrawsBackground_(False)
        restart_note.setEditable_(False)
        restart_note.setSelectable_(False)
        restart_note.setFont_(NSFont.systemFontOfSize_(10))
        restart_note.setTextColor_(NSColor.secondaryLabelColor())
        content_view.addSubview_(restart_note)

        y_pos -= 40

        # Separator
        sep3 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep3.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep3)

        y_pos -= 30

        # === CONTEXT SECTION ===
        context_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        context_title.setStringValue_("Context (for drafting mode)")
        context_title.setBezeled_(False)
        context_title.setDrawsBackground_(False)
        context_title.setEditable_(False)
        context_title.setSelectable_(False)
        context_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        content_view.addSubview_(context_title)

        y_pos -= 25

        self._context_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 18)
        )
        self._context_label.setStringValue_("No context set")
        self._context_label.setBezeled_(False)
        self._context_label.setDrawsBackground_(False)
        self._context_label.setEditable_(False)
        self._context_label.setSelectable_(False)
        self._context_label.setFont_(NSFont.systemFontOfSize_(11))
        self._context_label.setTextColor_(NSColor.secondaryLabelColor())
        content_view.addSubview_(self._context_label)

        y_pos -= 35

        # Context buttons
        set_context_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 130, 28)
        )
        set_context_btn.setTitle_("Set Context...")
        set_context_btn.setBezelStyle_(NSBezelStyleRounded)
        set_context_btn.setTarget_(self)
        set_context_btn.setAction_("setContext:")
        content_view.addSubview_(set_context_btn)

        clear_context_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(160, y_pos, 130, 28)
        )
        clear_context_btn.setTitle_("Clear Context")
        clear_context_btn.setBezelStyle_(NSBezelStyleRounded)
        clear_context_btn.setTarget_(self)
        clear_context_btn.setAction_("clearContext:")
        content_view.addSubview_(clear_context_btn)

        y_pos -= 50

        # Separator
        sep4 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep4.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep4)

        y_pos -= 40

        # Quit button
        quit_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 30)
        )
        quit_btn.setTitle_("Quit Dictation")
        quit_btn.setBezelStyle_(NSBezelStyleRounded)
        quit_btn.setTarget_(self)
        quit_btn.setAction_("quitApp:")
        content_view.addSubview_(quit_btn)

        y_pos -= 50

        # Separator
        sep5 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep5.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep5)

        y_pos -= 30

        # === CLIPBOARD HISTORY SECTION ===
        history_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        history_title.setStringValue_("Clipboard History")
        history_title.setBezeled_(False)
        history_title.setDrawsBackground_(False)
        history_title.setEditable_(False)
        history_title.setSelectable_(False)
        history_title.setFont_(NSFont.boldSystemFontOfSize_(14))
        content_view.addSubview_(history_title)

        y_pos -= 30

        # History action buttons
        refresh_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 100, 28)
        )
        refresh_btn.setTitle_("Refresh")
        refresh_btn.setBezelStyle_(NSBezelStyleRounded)
        refresh_btn.setTarget_(self)
        refresh_btn.setAction_("refreshHistory:")
        content_view.addSubview_(refresh_btn)

        clear_history_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(130, y_pos, 100, 28)
        )
        clear_history_btn.setTitle_("Clear All")
        clear_history_btn.setBezelStyle_(NSBezelStyleRounded)
        clear_history_btn.setTarget_(self)
        clear_history_btn.setAction_("clearHistory:")
        content_view.addSubview_(clear_history_btn)

        y_pos -= 35

        # History list container (scrollable area for history items)
        history_scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(20, y_pos - 250, width - 40, 280)
        )
        history_scroll.setHasVerticalScroller_(True)
        history_scroll.setHasHorizontalScroller_(False)
        history_scroll.setAutohidesScrollers_(True)
        history_scroll.setBorderType_(1)  # NSLineBorder

        # Container view for history items
        self._history_container = NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, width - 60, 280)
        )
        self._history_container.setWantsLayer_(True)

        history_scroll.setDocumentView_(self._history_container)
        content_view.addSubview_(history_scroll)

        # Load initial history
        self._populate_history()

        scroll_view.setDocumentView_(content_view)
        self._window.setContentView_(scroll_view)

    def show(self) -> None:
        """Show the control panel window."""
        print("Control panel show() called")
        if not HAS_APPKIT or not self._window:
            print("AppKit not available, cannot show control panel")
            return

        def _show():
            print("Showing control panel window...")
            self._window.setLevel_(3)  # NSFloatingWindowLevel
            self._window.makeKeyAndOrderFront_(None)
            self._window.center()
            NSApp.activateIgnoringOtherApps_(True)
            print("Control panel window should now be visible")

        self._run_on_main_thread(_show)

    def hide(self) -> None:
        """Hide the control panel window."""
        if not HAS_APPKIT or not self._window:
            return

        def _hide():
            self._window.orderOut_(None)

        self._run_on_main_thread(_hide)

    def set_state(self, state: str, language: Optional[str] = None) -> None:
        """Update the displayed state."""
        self._state = state

        def _update():
            if not self._status_label or not self._record_button:
                return

            if state == "idle":
                self._status_label.setStringValue_("Status: Ready")
                self._record_button.setTitle_("Start Recording")
                self._record_button.setEnabled_(True)
            elif state == "recording":
                self._status_label.setStringValue_("Status: Recording...")
                self._record_button.setTitle_("Stop Recording")
                self._record_button.setEnabled_(True)
            elif state == "processing":
                self._status_label.setStringValue_("Status: Processing...")
                self._record_button.setTitle_("Processing...")
                self._record_button.setEnabled_(False)
            elif state == "done":
                lang_str = f" ({language})" if language else ""
                self._status_label.setStringValue_(f"Status: Done{lang_str}")
                self._record_button.setTitle_("Start Recording")
                self._record_button.setEnabled_(True)
            elif state == "error":
                self._status_label.setStringValue_("Status: Error")
                self._record_button.setTitle_("Start Recording")
                self._record_button.setEnabled_(True)

        self._run_on_main_thread(_update)

    def update_context_status(self, has_context: bool) -> None:
        """Update the context status indicator."""
        self._has_context = has_context

        def _update():
            if self._context_label:
                if has_context:
                    self._context_label.setStringValue_("Context: Set")
                else:
                    self._context_label.setStringValue_("No context set")

        self._run_on_main_thread(_update)

    def toggleRecording_(self, sender) -> None:
        """Handle record button click."""
        if self.on_toggle_recording:
            self.on_toggle_recording()

    def modeChanged_(self, sender) -> None:
        """Handle mode popup change."""
        index = self._mode_popup.indexOfSelectedItem()
        drafting = index == 0
        self.generation_enabled = drafting

        # Save to config
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["enabled"] = drafting
        self._save_config()

        if self.on_mode_change:
            self.on_mode_change(drafting)

    def languageChanged_(self, sender) -> None:
        """Handle language popup change."""
        index = self._language_popup.indexOfSelectedItem()
        lang_map = {0: "auto", 1: "en", 2: "es"}
        lang = lang_map.get(index, "auto")

        # Save to config
        if "model" not in self._config:
            self._config["model"] = {}
        self._config["model"]["language"] = lang
        self._save_config()

        if self.on_language_change:
            self.on_language_change(lang)

    def whisperModelChanged_(self, sender) -> None:
        """Handle Whisper model change."""
        model = str(self._whisper_model_popup.titleOfSelectedItem())

        # Save to config
        if "model" not in self._config:
            self._config["model"] = {}
        self._config["model"]["name"] = model
        self._save_config()

        if self.on_settings_change:
            self.on_settings_change({"whisper_model": model})

    def aiModelChanged_(self, sender) -> None:
        """Handle AI model change."""
        model = str(self._ai_model_popup.titleOfSelectedItem())

        # Save to config
        if "generation" not in self._config:
            self._config["generation"] = {}
        self._config["generation"]["model"] = model
        self._save_config()

        if self.on_settings_change:
            self.on_settings_change({"ai_model": model})

    def hotkeyChanged_(self, sender) -> None:
        """Handle hotkey change."""
        hotkey = str(self._hotkey_field.stringValue())

        # Save to config
        if "behavior" not in self._config:
            self._config["behavior"] = {}
        self._config["behavior"]["hotkey"] = hotkey
        self._save_config()

        if self.on_settings_change:
            self.on_settings_change({"hotkey": hotkey})

    def stopKeyChanged_(self, sender) -> None:
        """Handle stop key change."""
        stop_key = str(self._stop_key_field.stringValue())

        # Save to config
        if "behavior" not in self._config:
            self._config["behavior"] = {}
        self._config["behavior"]["stop_key"] = stop_key
        self._save_config()

        if self.on_settings_change:
            self.on_settings_change({"stop_key": stop_key})

    def setContext_(self, sender) -> None:
        """Handle set context button click."""
        if self.on_set_context:
            self.on_set_context()

    def clearContext_(self, sender) -> None:
        """Handle clear context button click."""
        if self.on_clear_context:
            self.on_clear_context()
        self.update_context_status(False)

    def quitApp_(self, sender) -> None:
        """Handle quit button click."""
        if self.on_quit:
            self.on_quit()

    def refreshHistory_(self, sender) -> None:
        """Handle refresh history button click."""
        self._populate_history()

    def clearHistory_(self, sender) -> None:
        """Handle clear history button click."""
        if HAS_HISTORY:
            history = get_history()
            history.clear()
            self._populate_history()

    def _populate_history(self) -> None:
        """Populate the history list with entries."""
        if not HAS_APPKIT or not self._history_container:
            return

        def _update():
            # Clear existing buttons
            for btn in self._history_buttons:
                btn.removeFromSuperview()
            self._history_buttons.clear()

            if not HAS_HISTORY:
                # Show message that history is not available
                no_history_label = NSTextField.alloc().initWithFrame_(
                    NSMakeRect(10, 240, 300, 30)
                )
                no_history_label.setStringValue_("History module not available")
                no_history_label.setBezeled_(False)
                no_history_label.setDrawsBackground_(False)
                no_history_label.setEditable_(False)
                no_history_label.setSelectable_(False)
                no_history_label.setTextColor_(NSColor.secondaryLabelColor())
                self._history_container.addSubview_(no_history_label)
                return

            history = get_history()
            entries = history.get_recent(20)  # Show last 20 entries

            if not entries:
                # Show message that history is empty
                empty_label = NSTextField.alloc().initWithFrame_(
                    NSMakeRect(10, 240, 300, 30)
                )
                empty_label.setStringValue_("No history yet - dictate something!")
                empty_label.setBezeled_(False)
                empty_label.setDrawsBackground_(False)
                empty_label.setEditable_(False)
                empty_label.setSelectable_(False)
                empty_label.setTextColor_(NSColor.secondaryLabelColor())
                self._history_container.addSubview_(empty_label)
                self._history_buttons.append(empty_label)
                return

            # Calculate container height based on number of entries
            item_height = 60
            container_height = max(280, len(entries) * item_height + 10)
            container_width = self._history_container.frame().size.width

            self._history_container.setFrameSize_(
                NSMakeRect(0, 0, container_width, container_height).size
            )

            y_pos = container_height - item_height

            for idx, entry in enumerate(entries):
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(entry.timestamp)
                    time_str = dt.strftime("%m/%d %H:%M")
                except (ValueError, AttributeError):
                    time_str = "Unknown"

                # Truncate text for display
                display_text = entry.text[:80]
                if len(entry.text) > 80:
                    display_text += "..."

                # Mode indicator
                mode_indicator = "✨" if entry.mode == "drafting" else "📝"

                # Create container for this entry
                entry_view = NSView.alloc().initWithFrame_(
                    NSMakeRect(5, y_pos, container_width - 10, item_height - 5)
                )

                # Text label
                text_label = NSTextField.alloc().initWithFrame_(
                    NSMakeRect(5, 22, container_width - 80, 30)
                )
                text_label.setStringValue_(f"{mode_indicator} {display_text}")
                text_label.setBezeled_(False)
                text_label.setDrawsBackground_(False)
                text_label.setEditable_(False)
                text_label.setSelectable_(True)
                text_label.setFont_(NSFont.systemFontOfSize_(11))
                text_label.setLineBreakMode_(4)  # NSLineBreakByTruncatingTail
                entry_view.addSubview_(text_label)

                # Time and language label
                lang_str = f" ({entry.language})" if entry.language else ""
                meta_label = NSTextField.alloc().initWithFrame_(
                    NSMakeRect(5, 5, container_width - 80, 18)
                )
                meta_label.setStringValue_(f"{time_str}{lang_str}")
                meta_label.setBezeled_(False)
                meta_label.setDrawsBackground_(False)
                meta_label.setEditable_(False)
                meta_label.setSelectable_(False)
                meta_label.setFont_(NSFont.systemFontOfSize_(10))
                meta_label.setTextColor_(NSColor.secondaryLabelColor())
                entry_view.addSubview_(meta_label)

                # Copy button
                copy_btn = NSButton.alloc().initWithFrame_(
                    NSMakeRect(container_width - 70, 15, 60, 25)
                )
                copy_btn.setTitle_("Copy")
                copy_btn.setBezelStyle_(NSBezelStyleRounded)
                copy_btn.setFont_(NSFont.systemFontOfSize_(11))
                copy_btn.setTag_(idx)
                copy_btn.setTarget_(self)
                copy_btn.setAction_("copyHistoryItem:")
                entry_view.addSubview_(copy_btn)

                self._history_container.addSubview_(entry_view)
                self._history_buttons.append(entry_view)

                y_pos -= item_height

        self._run_on_main_thread(_update)

    def copyHistoryItem_(self, sender) -> None:
        """Handle copy button click for a history item."""
        index = sender.tag()

        if not HAS_HISTORY:
            return

        history = get_history()
        entry = history.get_by_index(index)

        if entry:
            # Copy to clipboard
            if HAS_PYPERCLIP:
                try:
                    pyperclip.copy(entry.text)
                    print(f"Copied history item {index} to clipboard")
                    # Update button text temporarily
                    self._show_copy_feedback(sender)
                except Exception as e:
                    print(f"Error copying to clipboard: {e}")
            else:
                # Fallback to pbcopy on macOS
                import subprocess
                try:
                    process = subprocess.Popen(
                        ['pbcopy'],
                        stdin=subprocess.PIPE,
                        env={'LANG': 'en_US.UTF-8'}
                    )
                    process.communicate(entry.text.encode('utf-8'))
                    print(f"Copied history item {index} to clipboard (via pbcopy)")
                    self._show_copy_feedback(sender)
                except Exception as e:
                    print(f"Error copying to clipboard: {e}")

    def _show_copy_feedback(self, button) -> None:
        """Show temporary feedback after copying."""
        def _update():
            original_title = button.title()
            button.setTitle_("Copied!")
            button.setEnabled_(False)

            def _restore():
                import time
                time.sleep(1.0)
                def _do_restore():
                    button.setTitle_(original_title)
                    button.setEnabled_(True)
                self._run_on_main_thread(_do_restore)

            threading.Thread(target=_restore, daemon=True).start()

        self._run_on_main_thread(_update)

    def _run_on_main_thread(self, func) -> None:
        """Run a function on the main thread."""
        try:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(func)
        except Exception:
            func()


def create_control_panel(
    on_toggle_recording: Optional[Callable[[], None]] = None,
    on_set_context: Optional[Callable[[], None]] = None,
    on_clear_context: Optional[Callable[[], None]] = None,
    on_mode_change: Optional[Callable[[bool], None]] = None,
    on_language_change: Optional[Callable[[str], None]] = None,
    on_quit: Optional[Callable[[], None]] = None,
    on_settings_change: Optional[Callable[[dict], None]] = None,
    generation_enabled: bool = True,
    generation_available: bool = True,
    config_path: Optional[str] = None,
):
    """Create a control panel window."""
    if HAS_APPKIT:
        return ControlPanelWindow(
            on_toggle_recording=on_toggle_recording,
            on_set_context=on_set_context,
            on_clear_context=on_clear_context,
            on_mode_change=on_mode_change,
            on_language_change=on_language_change,
            on_quit=on_quit,
            on_settings_change=on_settings_change,
            generation_enabled=generation_enabled,
            generation_available=generation_available,
            config_path=config_path,
        )
    else:
        print("Control panel requires AppKit (macOS)")
        return None
