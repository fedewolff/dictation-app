"""Text insertion into active applications."""

import subprocess
import time
from typing import Optional


class TextInserter:
    """Inserts text into the currently active application."""

    def __init__(self, method: str = "auto"):
        """Initialize text inserter.

        Args:
            method: Insertion method ('auto', 'clipboard', 'keystroke', 'clipboard_only')
        """
        self.method = method
        self._clipboard_backup: Optional[str] = None

    def insert(self, text: str) -> bool:
        """Insert text into active application.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        if not text:
            return True

        if self.method == "clipboard_only":
            return self._copy_to_clipboard_only(text)
        elif self.method == "auto" or self.method == "clipboard":
            return self._insert_via_clipboard(text)
        elif self.method == "keystroke":
            return self._insert_via_keystroke(text)
        else:
            return self._insert_via_clipboard(text)

    def _copy_to_clipboard_only(self, text: str) -> bool:
        """Copy text to clipboard without pasting.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        try:
            self._set_clipboard(text)
            return True
        except Exception as e:
            print(f"Clipboard copy failed: {e}")
            return False

    def _insert_via_clipboard(self, text: str) -> bool:
        """Insert text via clipboard and paste.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        try:
            # Backup current clipboard
            self._clipboard_backup = self._get_clipboard()

            # Set clipboard to our text
            self._set_clipboard(text)

            # Small delay to ensure clipboard is set
            time.sleep(0.05)

            # Simulate Cmd+V to paste
            self._simulate_paste()

            # Small delay before restoring
            time.sleep(0.1)

            # Restore clipboard (optional, can be disabled)
            if self._clipboard_backup:
                self._set_clipboard(self._clipboard_backup)

            return True

        except Exception as e:
            print(f"Clipboard insertion failed: {e}")
            # Try fallback
            return self._insert_via_keystroke(text)

    def _insert_via_keystroke(self, text: str) -> bool:
        """Insert text by simulating keystrokes.

        Args:
            text: Text to insert

        Returns:
            True if successful
        """
        try:
            import pyautogui

            # pyautogui.write doesn't handle unicode well
            # Use pyperclip + hotkey instead for unicode
            pyautogui.write(text, interval=0.01)
            return True

        except Exception as e:
            print(f"Keystroke insertion failed: {e}")
            return False

    def _get_clipboard(self) -> Optional[str]:
        """Get current clipboard contents.

        Returns:
            Clipboard text or None
        """
        try:
            result = subprocess.run(
                ["pbpaste"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            return result.stdout
        except Exception:
            return None

    def _set_clipboard(self, text: str) -> None:
        """Set clipboard contents.

        Args:
            text: Text to set
        """
        subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            timeout=1,
        )

    def _simulate_paste(self) -> None:
        """Simulate Cmd+V paste keystroke."""
        try:
            # Use AppleScript for reliable paste
            script = '''
            tell application "System Events"
                keystroke "v" using command down
            end tell
            '''
            subprocess.run(
                ["osascript", "-e", script],
                timeout=2,
                capture_output=True,
            )
        except Exception as e:
            # Fallback to pyautogui
            import pyautogui

            pyautogui.hotkey("command", "v")

    def type_text(self, text: str, interval: float = 0.01) -> bool:
        """Type text character by character (slow but reliable).

        Args:
            text: Text to type
            interval: Delay between characters

        Returns:
            True if successful
        """
        try:
            import pyautogui

            for char in text:
                pyautogui.press(char) if len(char) == 1 else None
                time.sleep(interval)
            return True
        except Exception as e:
            print(f"Typing failed: {e}")
            return False
