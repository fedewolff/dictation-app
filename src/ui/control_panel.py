"""Standalone control panel window for dictation app settings."""

import threading
from typing import Callable, Optional

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
    )
    from Foundation import NSObject

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


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
        generation_enabled: bool = True,
        generation_available: bool = True,
    ):
        """Initialize control panel window.

        Args:
            on_toggle_recording: Callback when recording is toggled
            on_set_context: Callback when 'Set Context' is clicked
            on_clear_context: Callback when 'Clear Context' is clicked
            on_mode_change: Callback when mode changes (receives True for drafting)
            on_language_change: Callback when language changes (receives lang code)
            on_quit: Callback when quit is clicked
            generation_enabled: Whether drafting mode is currently enabled
            generation_available: Whether drafting is available (Ollama running)
        """
        self.on_toggle_recording = on_toggle_recording
        self.on_set_context = on_set_context
        self.on_clear_context = on_clear_context
        self.on_mode_change = on_mode_change
        self.on_language_change = on_language_change
        self.on_quit = on_quit
        self.generation_enabled = generation_enabled
        self.generation_available = generation_available

        self._window = None
        self._status_label = None
        self._record_button = None
        self._mode_popup = None
        self._language_popup = None
        self._context_label = None
        self._context_buttons_view = None
        self._state = "idle"
        self._has_context = False

        if HAS_APPKIT:
            self._setup_window()

    def _setup_window(self) -> None:
        """Set up the control panel window using AppKit."""
        width = 340
        height = 450

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
        self._window.setMinSize_(NSMakeRect(0, 0, 300, 400).size)

        # Create content view
        content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        y_pos = height - 50

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

        y_pos -= 35

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

        y_pos -= 45

        # Record button (large, prominent)
        self._record_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 40)
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

        y_pos -= 35

        # Mode section
        mode_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 80, 20)
        )
        mode_label.setStringValue_("Mode:")
        mode_label.setBezeled_(False)
        mode_label.setDrawsBackground_(False)
        mode_label.setEditable_(False)
        mode_label.setSelectable_(False)
        mode_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(mode_label)

        self._mode_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(100, y_pos - 2, width - 120, 25)
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

        y_pos -= 40

        # Language section
        lang_label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, 80, 20)
        )
        lang_label.setStringValue_("Language:")
        lang_label.setBezeled_(False)
        lang_label.setDrawsBackground_(False)
        lang_label.setEditable_(False)
        lang_label.setSelectable_(False)
        lang_label.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(lang_label)

        self._language_popup = NSPopUpButton.alloc().initWithFrame_(
            NSMakeRect(100, y_pos - 2, width - 120, 25)
        )
        self._language_popup.addItemWithTitle_("Auto-detect")
        self._language_popup.addItemWithTitle_("English only")
        self._language_popup.addItemWithTitle_("Spanish only")
        self._language_popup.setTarget_(self)
        self._language_popup.setAction_("languageChanged:")
        content_view.addSubview_(self._language_popup)

        y_pos -= 45

        # Separator
        sep2 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep2.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep2)

        y_pos -= 35

        # Context section (only for drafting mode)
        context_title = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, y_pos, width - 40, 20)
        )
        context_title.setStringValue_("Context (for drafting mode)")
        context_title.setBezeled_(False)
        context_title.setDrawsBackground_(False)
        context_title.setEditable_(False)
        context_title.setSelectable_(False)
        context_title.setFont_(NSFont.boldSystemFontOfSize_(12))
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
        sep3 = NSBox.alloc().initWithFrame_(NSMakeRect(20, y_pos, width - 40, 1))
        sep3.setBoxType_(NSBoxSeparator)
        content_view.addSubview_(sep3)

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

        self._window.setContentView_(content_view)

    def show(self) -> None:
        """Show the control panel window."""
        print("Control panel show() called")
        if not HAS_APPKIT or not self._window:
            print("AppKit not available, cannot show control panel")
            return

        def _show():
            print("Showing control panel window...")
            # Set window level to floating so it appears above other windows
            self._window.setLevel_(3)  # NSFloatingWindowLevel
            self._window.makeKeyAndOrderFront_(None)
            self._window.center()  # Center on screen
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
        """Update the displayed state.

        Args:
            state: One of 'idle', 'recording', 'processing', 'done', 'error'
            language: Detected language code (for display)
        """
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
        """Update the context status indicator.

        Args:
            has_context: Whether context is currently set
        """
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
        if self.on_mode_change:
            self.on_mode_change(drafting)

    def languageChanged_(self, sender) -> None:
        """Handle language popup change."""
        index = self._language_popup.indexOfSelectedItem()
        lang_map = {0: "auto", 1: "en", 2: "es"}
        if self.on_language_change:
            self.on_language_change(lang_map.get(index, "auto"))

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
    generation_enabled: bool = True,
    generation_available: bool = True,
):
    """Create a control panel window.

    Args:
        on_toggle_recording: Callback when recording is toggled
        on_set_context: Callback when 'Set Context' is clicked
        on_clear_context: Callback when 'Clear Context' is clicked
        on_mode_change: Callback when mode changes
        on_language_change: Callback when language changes
        on_quit: Callback when quit is clicked
        generation_enabled: Whether drafting mode is currently enabled
        generation_available: Whether drafting is available

    Returns:
        ControlPanelWindow instance
    """
    if HAS_APPKIT:
        return ControlPanelWindow(
            on_toggle_recording=on_toggle_recording,
            on_set_context=on_set_context,
            on_clear_context=on_clear_context,
            on_mode_change=on_mode_change,
            on_language_change=on_language_change,
            on_quit=on_quit,
            generation_enabled=generation_enabled,
            generation_available=generation_available,
        )
    else:
        print("Control panel requires AppKit (macOS)")
        return None
