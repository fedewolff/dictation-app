"""Floating status indicator window."""

import threading
import time
from typing import Optional

try:
    from AppKit import (
        NSApplication,
        NSWindow,
        NSWindowStyleMaskBorderless,
        NSFloatingWindowLevel,
        NSBackingStoreBuffered,
        NSView,
        NSColor,
        NSFont,
        NSMakeRect,
        NSTextField,
        NSTextAlignmentCenter,
        NSScreen,
        NSAnimationContext,
    )
    from Foundation import NSObject

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class FloatingIndicator:
    """Floating status indicator that shows recording state."""

    # State configurations
    STATES = {
        "listening": {
            "text": "🎤 Listening...",
            "bg_color": (0.2, 0.2, 0.2, 0.9),
            "text_color": (1.0, 1.0, 1.0, 1.0),
        },
        "processing": {
            "text": "⚙️ Processing...",
            "bg_color": (0.2, 0.2, 0.3, 0.9),
            "text_color": (1.0, 1.0, 1.0, 1.0),
        },
        "done": {
            "text": "✓ Done",
            "bg_color": (0.1, 0.4, 0.1, 0.9),
            "text_color": (1.0, 1.0, 1.0, 1.0),
        },
        "error": {
            "text": "❌ Error",
            "bg_color": (0.4, 0.1, 0.1, 0.9),
            "text_color": (1.0, 1.0, 1.0, 1.0),
        },
    }

    def __init__(self, enabled: bool = True):
        """Initialize floating indicator.

        Args:
            enabled: Whether indicator is enabled
        """
        self.enabled = enabled
        self._window = None
        self._text_field = None
        self._visible = False
        self._auto_hide_timer: Optional[threading.Timer] = None

        if HAS_APPKIT and enabled:
            self._setup_window()

    def _setup_window(self) -> None:
        """Set up the floating window using AppKit."""
        # Window dimensions
        width = 180
        height = 50

        # Get screen dimensions and position window at top center
        screen = NSScreen.mainScreen()
        if screen:
            screen_frame = screen.frame()
            x = (screen_frame.size.width - width) / 2
            y = screen_frame.size.height - height - 100  # 100px from top
        else:
            x, y = 500, 800

        # Create window
        rect = NSMakeRect(x, y, width, height)
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            NSWindowStyleMaskBorderless,
            NSBackingStoreBuffered,
            False,
        )

        # Configure window
        self._window.setLevel_(NSFloatingWindowLevel)
        self._window.setOpaque_(False)
        self._window.setBackgroundColor_(NSColor.clearColor())
        self._window.setHasShadow_(True)
        self._window.setIgnoresMouseEvents_(True)
        self._window.setCollectionBehavior_(1 << 0)  # Can join all spaces

        # Create content view with rounded corners
        content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        # Create text field
        self._text_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(10, 10, width - 20, height - 20)
        )
        self._text_field.setStringValue_("Ready")
        self._text_field.setBezeled_(False)
        self._text_field.setDrawsBackground_(False)
        self._text_field.setEditable_(False)
        self._text_field.setSelectable_(False)
        self._text_field.setAlignment_(NSTextAlignmentCenter)
        self._text_field.setFont_(NSFont.systemFontOfSize_(16))
        self._text_field.setTextColor_(NSColor.whiteColor())

        content_view.addSubview_(self._text_field)
        self._window.setContentView_(content_view)

    def show(self, state: str = "listening") -> None:
        """Show the indicator with given state.

        Args:
            state: One of 'listening', 'processing', 'done', 'error'
        """
        if not self.enabled or not HAS_APPKIT:
            return

        # Cancel any pending auto-hide
        if self._auto_hide_timer:
            self._auto_hide_timer.cancel()
            self._auto_hide_timer = None

        def _show():
            if self._window is None:
                return

            config = self.STATES.get(state, self.STATES["listening"])

            # Update text
            self._text_field.setStringValue_(config["text"])

            # Update colors
            r, g, b, a = config["bg_color"]
            bg_color = NSColor.colorWithRed_green_blue_alpha_(r, g, b, a)

            r, g, b, a = config["text_color"]
            text_color = NSColor.colorWithRed_green_blue_alpha_(r, g, b, a)

            self._window.setBackgroundColor_(bg_color)
            self._text_field.setTextColor_(text_color)

            # Show window with fade-in
            self._window.setAlphaValue_(0.0)
            self._window.orderFrontRegardless()
            self._visible = True

            # Animate fade-in
            NSAnimationContext.beginGrouping()
            NSAnimationContext.currentContext().setDuration_(0.2)
            self._window.animator().setAlphaValue_(1.0)
            NSAnimationContext.endGrouping()

        # Run on main thread
        self._run_on_main_thread(_show)

    def update(self, state: str) -> None:
        """Update the indicator state.

        Args:
            state: One of 'listening', 'processing', 'done', 'error'
        """
        if not self.enabled or not HAS_APPKIT or not self._visible:
            self.show(state)
            return

        def _update():
            if self._window is None or self._text_field is None:
                return

            config = self.STATES.get(state, self.STATES["listening"])
            self._text_field.setStringValue_(config["text"])

            r, g, b, a = config["bg_color"]
            bg_color = NSColor.colorWithRed_green_blue_alpha_(r, g, b, a)
            self._window.setBackgroundColor_(bg_color)

        self._run_on_main_thread(_update)

    def hide(self, delay: float = 0.0) -> None:
        """Hide the indicator.

        Args:
            delay: Delay before hiding in seconds
        """
        if not self.enabled or not HAS_APPKIT:
            return

        if delay > 0:
            self._auto_hide_timer = threading.Timer(delay, self._do_hide)
            self._auto_hide_timer.start()
        else:
            self._do_hide()

    def _do_hide(self) -> None:
        """Actually hide the indicator."""

        def _hide():
            if self._window is None:
                return

            # Animate fade-out
            NSAnimationContext.beginGrouping()
            NSAnimationContext.currentContext().setDuration_(0.2)
            self._window.animator().setAlphaValue_(0.0)
            NSAnimationContext.endGrouping()

            # Hide after animation
            def _order_out():
                if self._window:
                    self._window.orderOut_(None)
                self._visible = False

            threading.Timer(0.25, lambda: self._run_on_main_thread(_order_out)).start()

        self._run_on_main_thread(_hide)

    def _run_on_main_thread(self, func) -> None:
        """Run a function on the main thread.

        Args:
            func: Function to run
        """
        try:
            from PyObjCTools import AppHelper

            AppHelper.callAfter(func)
        except Exception:
            # Fallback: just run directly
            func()

    def set_text(self, text: str) -> None:
        """Set custom text on the indicator.

        Args:
            text: Text to display
        """
        if not self.enabled or not HAS_APPKIT:
            return

        def _set():
            if self._text_field:
                self._text_field.setStringValue_(text)

        self._run_on_main_thread(_set)


# Fallback indicator using print (when AppKit is not available)
class PrintIndicator:
    """Simple print-based indicator when AppKit is not available."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def show(self, state: str = "listening") -> None:
        if self.enabled:
            print(f"[{state.upper()}]")

    def update(self, state: str) -> None:
        if self.enabled:
            print(f"[{state.upper()}]")

    def hide(self, delay: float = 0.0) -> None:
        pass

    def set_text(self, text: str) -> None:
        if self.enabled:
            print(f"[{text}]")


def create_indicator(enabled: bool = True):
    """Create the appropriate indicator based on available libraries.

    Args:
        enabled: Whether indicator should be enabled

    Returns:
        FloatingIndicator or PrintIndicator
    """
    if HAS_APPKIT:
        return FloatingIndicator(enabled)
    else:
        return PrintIndicator(enabled)
