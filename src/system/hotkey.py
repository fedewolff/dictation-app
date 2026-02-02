"""Global hotkey detection for macOS."""

import threading
from typing import Callable, Optional, Set

from pynput import keyboard


class HotkeyListener:
    """Listens for global hotkeys on macOS."""

    # Modifier key mappings
    MODIFIER_MAP = {
        "cmd": keyboard.Key.cmd,
        "command": keyboard.Key.cmd,
        "ctrl": keyboard.Key.ctrl,
        "control": keyboard.Key.ctrl,
        "alt": keyboard.Key.alt,
        "option": keyboard.Key.alt,
        "shift": keyboard.Key.shift,
    }

    def __init__(
        self,
        hotkey: str = "cmd+shift+space",
        on_press: Optional[Callable[[], None]] = None,
        on_release: Optional[Callable[[], None]] = None,
        mode: str = "push_to_talk",
        stop_key: str = "enter",
    ):
        """Initialize hotkey listener.

        Args:
            hotkey: Hotkey combination (e.g., 'cmd+shift+space')
            on_press: Callback when hotkey is pressed
            on_release: Callback when hotkey is released
            mode: 'push_to_talk', 'toggle', or 'separate_keys'
            stop_key: Key to stop recording in 'separate_keys' mode (default: 'enter')
        """
        self.on_press_callback = on_press
        self.on_release_callback = on_release
        self.mode = mode
        self.stop_key = stop_key

        self._parse_hotkey(hotkey)
        self._parse_stop_key(stop_key)

        self._listener: Optional[keyboard.Listener] = None
        self._pressed_modifiers: Set[keyboard.Key] = set()
        self._hotkey_active = False
        self._toggle_state = False
        self._recording_active = False  # Track if we're actively recording (for separate_keys mode)
        self._lock = threading.Lock()

    def _parse_hotkey(self, hotkey: str) -> None:
        """Parse hotkey string into components.

        Args:
            hotkey: Hotkey string like 'cmd+shift+space'
        """
        parts = hotkey.lower().replace(" ", "").split("+")

        self._required_modifiers: Set[keyboard.Key] = set()
        self._trigger_key: Optional[keyboard.Key] = None

        for part in parts:
            if part in self.MODIFIER_MAP:
                self._required_modifiers.add(self.MODIFIER_MAP[part])
            elif part == "space":
                self._trigger_key = keyboard.Key.space
            elif part == "tab":
                self._trigger_key = keyboard.Key.tab
            elif part == "enter":
                self._trigger_key = keyboard.Key.enter
            elif part == "esc":
                self._trigger_key = keyboard.Key.esc
            elif len(part) == 1:
                # Single character key
                self._trigger_key = keyboard.KeyCode.from_char(part)
            else:
                # Try as function key (f1-f12)
                if part.startswith("f") and part[1:].isdigit():
                    fn_num = int(part[1:])
                    if 1 <= fn_num <= 12:
                        self._trigger_key = getattr(keyboard.Key, part)

    def _parse_stop_key(self, stop_key: str) -> None:
        """Parse stop key string.

        Args:
            stop_key: Stop key string like 'enter' or 'esc'
        """
        stop_key = stop_key.lower().replace(" ", "")

        if stop_key == "space":
            self._stop_key = keyboard.Key.space
        elif stop_key == "tab":
            self._stop_key = keyboard.Key.tab
        elif stop_key == "enter":
            self._stop_key = keyboard.Key.enter
        elif stop_key == "esc":
            self._stop_key = keyboard.Key.esc
        elif len(stop_key) == 1:
            self._stop_key = keyboard.KeyCode.from_char(stop_key)
        else:
            # Try as function key
            if stop_key.startswith("f") and stop_key[1:].isdigit():
                fn_num = int(stop_key[1:])
                if 1 <= fn_num <= 12:
                    self._stop_key = getattr(keyboard.Key, stop_key)
            else:
                self._stop_key = keyboard.Key.enter  # Default to enter

    def _on_press(self, key) -> None:
        """Handle key press event.

        Args:
            key: The key that was pressed
        """
        with self._lock:
            # Track modifier keys
            if isinstance(key, keyboard.Key):
                if key in (
                    keyboard.Key.cmd,
                    keyboard.Key.cmd_l,
                    keyboard.Key.cmd_r,
                ):
                    self._pressed_modifiers.add(keyboard.Key.cmd)
                elif key in (
                    keyboard.Key.ctrl,
                    keyboard.Key.ctrl_l,
                    keyboard.Key.ctrl_r,
                ):
                    self._pressed_modifiers.add(keyboard.Key.ctrl)
                elif key in (
                    keyboard.Key.alt,
                    keyboard.Key.alt_l,
                    keyboard.Key.alt_r,
                ):
                    self._pressed_modifiers.add(keyboard.Key.alt)
                elif key in (
                    keyboard.Key.shift,
                    keyboard.Key.shift_l,
                    keyboard.Key.shift_r,
                ):
                    self._pressed_modifiers.add(keyboard.Key.shift)

            # For separate_keys mode, check if stop key is pressed while recording
            if self.mode == "separate_keys" and self._recording_active:
                if self._is_stop_key(key):
                    self._recording_active = False
                    self._trigger_release()
                    return

            # Check if hotkey combination is pressed
            if self._is_hotkey_pressed(key):
                if not self._hotkey_active:
                    self._hotkey_active = True

                    if self.mode == "toggle":
                        self._toggle_state = not self._toggle_state
                        if self._toggle_state:
                            self._trigger_press()
                        else:
                            self._trigger_release()
                    elif self.mode == "separate_keys":
                        # Start recording only if not already recording
                        if not self._recording_active:
                            self._recording_active = True
                            self._trigger_press()
                    else:  # push_to_talk
                        self._trigger_press()

    def _on_release(self, key) -> None:
        """Handle key release event.

        Args:
            key: The key that was released
        """
        with self._lock:
            # Track modifier keys
            if isinstance(key, keyboard.Key):
                if key in (
                    keyboard.Key.cmd,
                    keyboard.Key.cmd_l,
                    keyboard.Key.cmd_r,
                ):
                    self._pressed_modifiers.discard(keyboard.Key.cmd)
                elif key in (
                    keyboard.Key.ctrl,
                    keyboard.Key.ctrl_l,
                    keyboard.Key.ctrl_r,
                ):
                    self._pressed_modifiers.discard(keyboard.Key.ctrl)
                elif key in (
                    keyboard.Key.alt,
                    keyboard.Key.alt_l,
                    keyboard.Key.alt_r,
                ):
                    self._pressed_modifiers.discard(keyboard.Key.alt)
                elif key in (
                    keyboard.Key.shift,
                    keyboard.Key.shift_l,
                    keyboard.Key.shift_r,
                ):
                    self._pressed_modifiers.discard(keyboard.Key.shift)

            # Check if hotkey was released (for push_to_talk mode)
            if self._hotkey_active:
                if self.mode == "push_to_talk":
                    # Trigger release when any part of hotkey is released
                    if self._is_trigger_key(key) or not self._modifiers_held():
                        self._hotkey_active = False
                        self._trigger_release()
                elif self.mode == "separate_keys":
                    # Just reset hotkey_active, don't trigger release
                    # (release happens on stop key press)
                    if self._is_trigger_key(key):
                        self._hotkey_active = False
                else:  # toggle mode
                    # Just reset hotkey_active, don't trigger release
                    if self._is_trigger_key(key):
                        self._hotkey_active = False

    def _is_hotkey_pressed(self, key) -> bool:
        """Check if the full hotkey combination is pressed.

        Args:
            key: The key being pressed

        Returns:
            True if hotkey is pressed
        """
        # Check if all required modifiers are held
        if not self._required_modifiers.issubset(self._pressed_modifiers):
            return False

        # Check if trigger key matches
        return self._is_trigger_key(key)

    def _is_trigger_key(self, key) -> bool:
        """Check if key matches the trigger key.

        Args:
            key: Key to check

        Returns:
            True if it's the trigger key
        """
        if self._trigger_key is None:
            return False

        if isinstance(self._trigger_key, keyboard.Key):
            return key == self._trigger_key
        elif isinstance(self._trigger_key, keyboard.KeyCode):
            if isinstance(key, keyboard.KeyCode):
                return key.char == self._trigger_key.char
        return False

    def _is_stop_key(self, key) -> bool:
        """Check if key matches the stop key.

        Args:
            key: Key to check

        Returns:
            True if it's the stop key
        """
        if not hasattr(self, '_stop_key') or self._stop_key is None:
            return False

        if isinstance(self._stop_key, keyboard.Key):
            return key == self._stop_key
        elif isinstance(self._stop_key, keyboard.KeyCode):
            if isinstance(key, keyboard.KeyCode):
                return key.char == self._stop_key.char
        return False

    def _modifiers_held(self) -> bool:
        """Check if all required modifiers are still held.

        Returns:
            True if all modifiers are held
        """
        return self._required_modifiers.issubset(self._pressed_modifiers)

    def _trigger_press(self) -> None:
        """Trigger the press callback."""
        if self.on_press_callback:
            # Run callback in separate thread to avoid blocking listener
            threading.Thread(target=self.on_press_callback, daemon=True).start()

    def _trigger_release(self) -> None:
        """Trigger the release callback."""
        if self.on_release_callback:
            threading.Thread(target=self.on_release_callback, daemon=True).start()

    def start(self) -> None:
        """Start listening for hotkeys."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            self._pressed_modifiers.clear()
            self._hotkey_active = False

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._listener is not None and self._listener.is_alive()
