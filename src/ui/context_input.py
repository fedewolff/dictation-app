"""Context input window for providing optional context to message generation."""

import threading
from typing import Callable, Optional

try:
    from AppKit import (
        NSApplication,
        NSWindow,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSBackingStoreBuffered,
        NSView,
        NSColor,
        NSFont,
        NSMakeRect,
        NSTextField,
        NSTextView,
        NSScrollView,
        NSButton,
        NSScreen,
        NSBezelStyleRounded,
        NSApp,
    )
    from Foundation import NSObject

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


class ContextInputWindow:
    """Window for entering optional context for message generation."""

    def __init__(
        self,
        on_save: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
    ):
        """Initialize context input window.

        Args:
            on_save: Callback when context is saved (receives context text)
            on_clear: Callback when context is cleared
        """
        self.on_save = on_save
        self.on_clear = on_clear
        self._window = None
        self._text_view = None
        self._current_context = ""

        if HAS_APPKIT:
            self._setup_window()

    def _setup_window(self) -> None:
        """Set up the context input window using AppKit."""
        # Window dimensions
        width = 500
        height = 350

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
        style = NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
        self._window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style,
            NSBackingStoreBuffered,
            False,
        )

        # Configure window
        self._window.setTitle_("Set Context (Optional)")
        self._window.setReleasedWhenClosed_(False)

        # Create content view
        content_view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        # Instructions label
        instructions = NSTextField.alloc().initWithFrame_(
            NSMakeRect(20, height - 50, width - 40, 30)
        )
        instructions.setStringValue_(
            "Enter optional context (e.g., previous email, data points):"
        )
        instructions.setBezeled_(False)
        instructions.setDrawsBackground_(False)
        instructions.setEditable_(False)
        instructions.setSelectable_(False)
        instructions.setFont_(NSFont.systemFontOfSize_(13))
        content_view.addSubview_(instructions)

        # Text view inside scroll view for multi-line input
        scroll_rect = NSMakeRect(20, 70, width - 40, height - 130)
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_rect)
        scroll_view.setBorderType_(1)  # NSBezelBorder
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutohidesScrollers_(True)

        # Text view
        text_rect = NSMakeRect(0, 0, scroll_rect.size.width - 20, scroll_rect.size.height)
        self._text_view = NSTextView.alloc().initWithFrame_(text_rect)
        self._text_view.setMinSize_(NSMakeRect(0, 0, scroll_rect.size.width - 20, scroll_rect.size.height).size)
        self._text_view.setMaxSize_(NSMakeRect(0, 0, 10000, 10000).size)
        self._text_view.setVerticallyResizable_(True)
        self._text_view.setHorizontallyResizable_(False)
        self._text_view.setFont_(NSFont.systemFontOfSize_(13))
        self._text_view.textContainer().setWidthTracksTextView_(True)

        scroll_view.setDocumentView_(self._text_view)
        content_view.addSubview_(scroll_view)

        # Buttons
        button_y = 20

        # Clear button
        clear_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(20, button_y, 100, 30)
        )
        clear_btn.setTitle_("Clear")
        clear_btn.setBezelStyle_(NSBezelStyleRounded)
        clear_btn.setTarget_(self)
        clear_btn.setAction_("clearContext:")
        content_view.addSubview_(clear_btn)

        # Cancel button
        cancel_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(width - 220, button_y, 100, 30)
        )
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_("cancelInput:")
        content_view.addSubview_(cancel_btn)

        # Save button
        save_btn = NSButton.alloc().initWithFrame_(
            NSMakeRect(width - 110, button_y, 90, 30)
        )
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_("saveContext:")
        content_view.addSubview_(save_btn)

        self._window.setContentView_(content_view)

    def show(self, current_context: str = "") -> None:
        """Show the context input window.

        Args:
            current_context: Current context text to display
        """
        if not HAS_APPKIT or not self._window:
            print("AppKit not available, cannot show context window")
            return

        def _show():
            # Set current context
            if self._text_view:
                self._text_view.setString_(current_context or "")

            # Show window
            self._window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)

        self._run_on_main_thread(_show)

    def hide(self) -> None:
        """Hide the context input window."""
        if not HAS_APPKIT or not self._window:
            return

        def _hide():
            self._window.orderOut_(None)

        self._run_on_main_thread(_hide)

    def saveContext_(self, sender) -> None:
        """Handle save button click."""
        if self._text_view:
            context = self._text_view.string()
            self._current_context = context
            if self.on_save:
                self.on_save(context)
        self.hide()

    def clearContext_(self, sender) -> None:
        """Handle clear button click."""
        if self._text_view:
            self._text_view.setString_("")
        self._current_context = ""
        if self.on_clear:
            self.on_clear()
        self.hide()

    def cancelInput_(self, sender) -> None:
        """Handle cancel button click."""
        self.hide()

    def _run_on_main_thread(self, func) -> None:
        """Run a function on the main thread."""
        try:
            from PyObjCTools import AppHelper

            AppHelper.callAfter(func)
        except Exception:
            func()


class PrintContextInput:
    """Fallback context input when AppKit is not available."""

    def __init__(
        self,
        on_save: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
    ):
        self.on_save = on_save
        self.on_clear = on_clear
        print("Note: Context input window not available (AppKit required)")

    def show(self, current_context: str = "") -> None:
        print("Context window not available. Set context via config or environment.")

    def hide(self) -> None:
        pass


def create_context_input(
    on_save: Optional[Callable[[str], None]] = None,
    on_clear: Optional[Callable[[], None]] = None,
):
    """Create the appropriate context input based on available libraries.

    Args:
        on_save: Callback when context is saved
        on_clear: Callback when context is cleared

    Returns:
        ContextInputWindow or PrintContextInput
    """
    if HAS_APPKIT:
        return ContextInputWindow(on_save=on_save, on_clear=on_clear)
    else:
        return PrintContextInput(on_save=on_save, on_clear=on_clear)
