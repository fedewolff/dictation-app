"""Menu bar application for macOS."""

import threading
from typing import Callable, Optional

import rumps


class MenuBarApp(rumps.App):
    """System tray / menu bar application."""

    # Menu bar icons (using emoji for simplicity, can be replaced with actual icons)
    ICON_IDLE = None  # Will show title
    ICON_RECORDING = None
    ICON_PROCESSING = None

    def __init__(
        self,
        on_toggle_recording: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_set_context: Optional[Callable[[], None]] = None,
        on_clear_context: Optional[Callable[[], None]] = None,
        on_toggle_mode: Optional[Callable[[bool], None]] = None,
        on_show_control_panel: Optional[Callable[[], None]] = None,
        generation_enabled: bool = True,
        generation_available: bool = True,
    ):
        """Initialize menu bar app.

        Args:
            on_toggle_recording: Callback when recording is toggled from menu
            on_quit: Callback when quit is selected
            on_set_context: Callback when 'Set Context' is selected
            on_clear_context: Callback when 'Clear Context' is selected
            on_toggle_mode: Callback when mode is toggled (receives new state: True=drafting)
            on_show_control_panel: Callback when 'Show Control Panel' is selected
            generation_enabled: Whether generative drafting mode is currently enabled
            generation_available: Whether generative drafting is available (Ollama running)
        """
        super().__init__(
            name="Dictation",
            title="Dictation",
            quit_button=None,  # We'll add our own
        )

        self.on_toggle_recording = on_toggle_recording
        self.on_quit_callback = on_quit
        self.on_set_context_callback = on_set_context
        self.on_clear_context_callback = on_clear_context
        self.on_toggle_mode_callback = on_toggle_mode
        self.on_show_control_panel_callback = on_show_control_panel
        self.generation_enabled = generation_enabled
        self.generation_available = generation_available

        self._state = "idle"
        self._language = "auto"
        self._has_context = False

        # Build menu
        self._build_menu()

    def _build_menu(self) -> None:
        """Build the menu bar menu."""
        # Status item (not clickable, just shows state)
        self.status_item = rumps.MenuItem("Status: Ready")
        self.status_item.set_callback(None)

        # Mode submenu
        self.mode_drafting = rumps.MenuItem("Drafting", callback=self._set_mode_drafting)
        self.mode_transcription = rumps.MenuItem("Transcription", callback=self._set_mode_transcription)

        # Set initial checkmarks
        if self.generation_enabled:
            self.mode_drafting.state = 1
            self.mode_transcription.state = 0
        else:
            self.mode_drafting.state = 0
            self.mode_transcription.state = 1

        # Disable drafting option if not available
        if not self.generation_available:
            self.mode_drafting.set_callback(None)
            self.mode_drafting.title = "Drafting (Ollama not running)"

        self.mode_menu = rumps.MenuItem("Mode")
        self.mode_menu.add(self.mode_drafting)
        self.mode_menu.add(self.mode_transcription)

        # Language item
        self.language_item = rumps.MenuItem(f"Language: Auto-detect")

        # Toggle recording
        self.record_item = rumps.MenuItem("Start Recording", callback=self._on_record)

        # Separator
        separator1 = rumps.separator

        # Context menu items (only shown if generation is enabled)
        self.context_item = rumps.MenuItem("Context: None", callback=None)
        self.context_item.set_callback(None)
        self.set_context_item = rumps.MenuItem("Set Context...", callback=self._on_set_context)
        self.clear_context_item = rumps.MenuItem("Clear Context", callback=self._on_clear_context)

        # Language submenu
        self.lang_auto = rumps.MenuItem("Auto-detect", callback=self._set_lang_auto)
        self.lang_en = rumps.MenuItem("English only", callback=self._set_lang_en)
        self.lang_es = rumps.MenuItem("Spanish only", callback=self._set_lang_es)
        self.lang_auto.state = 1  # Checked

        language_menu = rumps.MenuItem("Language")
        language_menu.add(self.lang_auto)
        language_menu.add(self.lang_en)
        language_menu.add(self.lang_es)

        # Separator
        separator2 = rumps.separator

        # Control Panel
        self.control_panel_item = rumps.MenuItem(
            "Open Control Panel...", callback=self._on_show_control_panel
        )

        # Quit
        quit_item = rumps.MenuItem("Quit Dictation", callback=self._on_quit)

        # Add items to menu
        menu_items = [
            self.status_item,
            separator1,
            self.record_item,
            self.mode_menu,
        ]

        # Add context items only if generation is enabled
        if self.generation_enabled:
            menu_items.extend([
                rumps.separator,
                self.context_item,
                self.set_context_item,
                self.clear_context_item,
            ])

        menu_items.extend([
            rumps.separator,
            language_menu,
            separator2,
            self.control_panel_item,
            quit_item,
        ])

        self.menu = menu_items

    def _on_record(self, sender) -> None:
        """Handle record menu item click."""
        if self.on_toggle_recording:
            self.on_toggle_recording()

    def _on_quit(self, sender) -> None:
        """Handle quit menu item click."""
        if self.on_quit_callback:
            self.on_quit_callback()
        rumps.quit_application()

    def _on_set_context(self, sender) -> None:
        """Handle set context menu item click."""
        if self.on_set_context_callback:
            self.on_set_context_callback()

    def _on_clear_context(self, sender) -> None:
        """Handle clear context menu item click."""
        if self.on_clear_context_callback:
            self.on_clear_context_callback()
        self.update_context_status(False)

    def _on_show_control_panel(self, sender) -> None:
        """Handle show control panel menu item click."""
        if self.on_show_control_panel_callback:
            self.on_show_control_panel_callback()

    def _set_mode_drafting(self, sender) -> None:
        """Set mode to drafting."""
        if not self.generation_available:
            return
        self.generation_enabled = True
        self.mode_drafting.state = 1
        self.mode_transcription.state = 0
        # Enable context menu items
        self.context_item.title = "Context: None" if not self._has_context else "Context: Set ✓"
        self.set_context_item.set_callback(self._on_set_context)
        self.clear_context_item.set_callback(self._on_clear_context)
        if self.on_toggle_mode_callback:
            self.on_toggle_mode_callback(True)

    def _set_mode_transcription(self, sender) -> None:
        """Set mode to transcription."""
        self.generation_enabled = False
        self.mode_drafting.state = 0
        self.mode_transcription.state = 1
        # Disable context menu items (grey them out)
        self.context_item.title = "Context: (N/A in transcription mode)"
        self.set_context_item.set_callback(None)
        self.clear_context_item.set_callback(None)
        if self.on_toggle_mode_callback:
            self.on_toggle_mode_callback(False)

    def _set_lang_auto(self, sender) -> None:
        """Set language to auto-detect."""
        self._language = "auto"
        self.lang_auto.state = 1
        self.lang_en.state = 0
        self.lang_es.state = 0
        self.language_item.title = "Language: Auto-detect"

    def _set_lang_en(self, sender) -> None:
        """Set language to English only."""
        self._language = "en"
        self.lang_auto.state = 0
        self.lang_en.state = 1
        self.lang_es.state = 0
        self.language_item.title = "Language: English"

    def _set_lang_es(self, sender) -> None:
        """Set language to Spanish only."""
        self._language = "es"
        self.lang_auto.state = 0
        self.lang_en.state = 0
        self.lang_es.state = 1
        self.language_item.title = "Language: Spanish"

    def set_state(self, state: str, language: Optional[str] = None) -> None:
        """Set the current state of the app.

        Args:
            state: One of 'idle', 'recording', 'processing', 'done', 'error'
            language: Detected language code (for display)
        """
        self._state = state

        # Update title/icon based on state
        if state == "idle":
            self.title = "Dictation"
            self.status_item.title = "Status: Ready"
            self.record_item.title = "Start Recording"
        elif state == "recording":
            self.title = "🔴 Recording"
            self.status_item.title = "Status: Recording..."
            self.record_item.title = "Stop Recording"
        elif state == "processing":
            self.title = "⚙️ Processing"
            self.status_item.title = "Status: Processing..."
            self.record_item.title = "Processing..."
        elif state == "done":
            lang_str = f" ({language})" if language else ""
            self.title = "✓ Done"
            self.status_item.title = f"Status: Done{lang_str}"
            self.record_item.title = "Start Recording"
            # Auto-reset to idle after a moment
            threading.Timer(1.5, lambda: self.set_state("idle")).start()
        elif state == "error":
            self.title = "❌ Error"
            self.status_item.title = "Status: Error"
            self.record_item.title = "Start Recording"

    @property
    def language(self) -> Optional[str]:
        """Get the selected language.

        Returns:
            Language code or None for auto-detect
        """
        return None if self._language == "auto" else self._language

    def update_context_status(self, has_context: bool) -> None:
        """Update the context status indicator in the menu.

        Args:
            has_context: Whether context is currently set
        """
        self._has_context = has_context
        if self.generation_enabled:
            if has_context:
                self.context_item.title = "Context: Set ✓"
            else:
                self.context_item.title = "Context: None"

    def run_detached(self) -> threading.Thread:
        """Run the menu bar app in a separate thread.

        Returns:
            The thread running the app
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
