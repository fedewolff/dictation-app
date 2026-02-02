#!/usr/bin/env python3
"""
Dictation App - Local speech-to-text with Whisper.

A macOS dictation application using OpenAI Whisper for local transcription.
Supports Spanish and English with automatic language detection.
"""

import signal
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.capture import AudioCapture
from src.audio.vad import VoiceActivityDetector
from src.config.settings import Settings
from src.generation.drafting import MessageDrafter
from src.system.hotkey import HotkeyListener
from src.system.insertion import TextInserter
from src.system.tray import MenuBarApp
from src.transcription.engine import WhisperEngine
from src.transcription.processor import TextProcessor
from src.ui.context_input import create_context_input
from src.ui.control_panel import create_control_panel
from src.ui.indicator import create_indicator


class DictationApp:
    """Main dictation application controller."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the dictation app.

        Args:
            config_path: Path to configuration file
        """
        print("Initializing Dictation App...")

        # Load configuration
        self.settings = Settings(config_path)

        # Initialize components
        self._init_audio()
        self._init_transcription()
        self._init_system()
        self._init_ui()

        # State
        self._is_recording = False
        self._lock = threading.Lock()
        self._running = True

    def _init_audio(self) -> None:
        """Initialize audio components."""
        self.audio_capture = AudioCapture(
            sample_rate=self.settings.sample_rate,
            device=self.settings.audio_device
            if self.settings.audio_device != "default"
            else None,
        )
        self.vad = VoiceActivityDetector(sample_rate=self.settings.sample_rate)

    def _init_transcription(self) -> None:
        """Initialize transcription components."""
        self.whisper = WhisperEngine(
            model_name=self.settings.model_name,
            device=self.settings.device,
            compute_type=self.settings.compute_type,
            language=self.settings.model_language,
        )
        self.processor = TextProcessor(
            custom_commands=self.settings.custom_commands,
            enable_commands=self.settings.voice_commands_enabled,
        )

        # Initialize message drafter for generative mode
        self.generation_enabled = self.settings.generation_enabled
        self.drafter = None
        if self.generation_enabled:
            self.drafter = MessageDrafter(
                api_key=self.settings.generation_api_key,
                provider=self.settings.generation_provider,
                model=self.settings.generation_model,
                ollama_host=self.settings.ollama_host,
            )
            if not self.drafter.is_configured():
                print("Warning: Generation enabled but not properly configured.")
                print("Falling back to transcription mode.")
                self.generation_enabled = False
            elif self.settings.generation_provider == "ollama":
                # Check if Ollama is available
                if not self.drafter.check_ollama_available():
                    print("Falling back to transcription mode.")
                    self.generation_enabled = False

        # Optional context for message generation
        self._context: Optional[str] = None

    def _init_system(self) -> None:
        """Initialize system integration components."""
        self.inserter = TextInserter(method=self.settings.insertion_method)
        self.hotkey = HotkeyListener(
            hotkey=self.settings.hotkey,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            mode=self.settings.recording_mode,
            stop_key=self.settings.stop_key,
        )

    def _init_ui(self) -> None:
        """Initialize UI components."""
        self.indicator = create_indicator(enabled=self.settings.show_indicator)

        # Context input window (for generative mode)
        self.context_window = create_context_input(
            on_save=self._on_context_save,
            on_clear=self._on_context_clear,
        )

        # Track if generation is available (Ollama running, etc.)
        self._generation_available = self.generation_enabled

        self.menu_bar = MenuBarApp(
            on_toggle_recording=self._toggle_recording,
            on_quit=self._on_quit,
            on_set_context=self._show_context_window,
            on_clear_context=self._on_context_clear,
            on_toggle_mode=self._on_mode_toggle,
            on_show_control_panel=self.show_control_panel,
            generation_enabled=self.generation_enabled,
            generation_available=self._generation_available,
        )

        # Control panel window (standalone settings access)
        self.control_panel = create_control_panel(
            on_toggle_recording=self._toggle_recording,
            on_set_context=self._show_context_window,
            on_clear_context=self._on_context_clear,
            on_mode_change=self._on_mode_toggle,
            on_language_change=self._on_language_change,
            on_quit=self._on_quit,
            generation_enabled=self.generation_enabled,
            generation_available=self._generation_available,
        )

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press - start recording."""
        with self._lock:
            if self._is_recording:
                return
            self._start_recording()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release - stop recording and transcribe."""
        with self._lock:
            if not self._is_recording:
                return
            self._stop_and_transcribe()

    def _toggle_recording(self) -> None:
        """Toggle recording state (for menu bar button)."""
        with self._lock:
            if self._is_recording:
                self._stop_and_transcribe()
            else:
                self._start_recording()

    def _start_recording(self) -> None:
        """Start audio recording."""
        self._is_recording = True

        # Update UI
        self.indicator.show("listening")
        self.menu_bar.set_state("recording")
        if self.control_panel:
            self.control_panel.set_state("recording")

        # Start capture
        self.audio_capture.start()
        print("Recording started...")

    def _stop_and_transcribe(self) -> None:
        """Stop recording and transcribe audio."""
        # Get audio
        audio = self.audio_capture.stop()
        self._is_recording = False

        # Update UI
        self.indicator.update("processing")
        self.menu_bar.set_state("processing")
        if self.control_panel:
            self.control_panel.set_state("processing")
        print(f"Recording stopped. Duration: {len(audio) / 16000:.1f}s")

        # Process in background to not block
        threading.Thread(target=self._process_audio, args=(audio,), daemon=True).start()

    def _process_audio(self, audio) -> None:
        """Process recorded audio (runs in background thread).

        Args:
            audio: Audio samples as numpy array
        """
        try:
            # Check minimum duration
            if len(audio) < 8000:  # Less than 0.5 seconds
                print("Recording too short, skipping...")
                self.indicator.hide(delay=0.5)
                self.menu_bar.set_state("idle")
                if self.control_panel:
                    self.control_panel.set_state("idle")
                return

            # Trim silence with VAD (optional, Whisper has built-in VAD)
            # audio, has_speech = self.vad.trim_silence(audio)
            # if not has_speech:
            #     print("No speech detected")
            #     self.indicator.hide(delay=0.5)
            #     self.menu_bar.set_state("idle")
            #     return

            # Transcribe
            print("Transcribing...")
            result = self.whisper.transcribe(audio)

            if not result.text:
                print("No text transcribed")
                self.indicator.hide(delay=0.5)
                self.menu_bar.set_state("idle")
                if self.control_panel:
                    self.control_panel.set_state("idle")
                return

            print(f"Detected language: {result.language}")
            print(f"Raw transcription: {result.text}")

            # Generate or process text based on mode
            if self.generation_enabled and self.drafter:
                # Generative mode: transform intent into professional message
                print("Generating message from intent...")
                self.indicator.set_text("✨ Drafting...")
                final_text = self.drafter.draft(
                    intent=result.text,
                    context=self._context,
                    language=result.language,
                )
                print(f"Generated message: {final_text}")
            else:
                # Transcription mode: process text (voice commands, cleanup)
                final_text = self.processor.process(result.text, result.language)
                print(f"Processed text: {final_text}")

            # Update UI to done state
            self.indicator.update("done")
            self.menu_bar.set_state("done", result.language)
            if self.control_panel:
                self.control_panel.set_state("done", result.language)

            # Insert text
            success = self.inserter.insert(final_text)
            if success:
                print("Text inserted successfully")
            else:
                print("Failed to insert text")
                self.indicator.set_text("❌ Insert failed")

            # Hide indicator after a moment
            self.indicator.hide(delay=1.0)

        except Exception as e:
            print(f"Error processing audio: {e}")
            self.indicator.update("error")
            self.indicator.set_text(f"❌ {str(e)[:20]}")
            self.indicator.hide(delay=2.0)
            self.menu_bar.set_state("error")
            if self.control_panel:
                self.control_panel.set_state("error")

    def _on_quit(self) -> None:
        """Handle quit request."""
        print("Shutting down...")
        self._running = False
        self.hotkey.stop()

    def _show_context_window(self) -> None:
        """Show the context input window."""
        self.context_window.show(self._context or "")

    def show_control_panel(self) -> None:
        """Show the standalone control panel window."""
        if self.control_panel:
            self.control_panel.show()

    def _on_context_save(self, context: str) -> None:
        """Handle context being saved from the UI."""
        self.set_context(context)
        has_context = bool(context and context.strip())
        self.menu_bar.update_context_status(has_context)
        if self.control_panel:
            self.control_panel.update_context_status(has_context)

    def _on_context_clear(self) -> None:
        """Handle context being cleared from the UI."""
        self.clear_context()
        self.menu_bar.update_context_status(False)
        if self.control_panel:
            self.control_panel.update_context_status(False)

    def _on_mode_toggle(self, drafting_enabled: bool) -> None:
        """Handle mode toggle from menu bar or control panel.

        Args:
            drafting_enabled: True for drafting mode, False for transcription
        """
        self.generation_enabled = drafting_enabled
        mode_name = "Drafting" if drafting_enabled else "Transcription"
        print(f"Mode changed to: {mode_name}")

    def _on_language_change(self, language: str) -> None:
        """Handle language change from control panel.

        Args:
            language: Language code ('auto', 'en', 'es')
        """
        # Update whisper engine language setting
        lang = None if language == "auto" else language
        self.whisper.language = lang
        print(f"Language changed to: {language}")

    def set_context(self, context: Optional[str]) -> None:
        """Set optional context for message generation.

        Args:
            context: Context text (e.g., previous email content) or None to clear
        """
        self._context = context.strip() if context else None
        if self._context:
            print(f"Context set ({len(self._context)} chars)")
        else:
            print("Context cleared")

    def clear_context(self) -> None:
        """Clear the optional context."""
        self._context = None
        print("Context cleared")

    def has_context(self) -> bool:
        """Check if context is currently set."""
        return bool(self._context)

    def preload_model(self) -> None:
        """Preload the Whisper model for faster first transcription."""
        print("Preloading Whisper model (this may take a moment)...")
        self.whisper.preload()
        print("Model preloaded and ready!")

    def run(self) -> None:
        """Run the dictation app."""
        print("Starting Dictation App...")
        print(f"Recording mode: {self.settings.recording_mode}")
        print(f"Whisper model: {self.settings.model_name}")
        if self.generation_enabled:
            print(f"Output mode: Generative drafting ({self.settings.generation_provider})")
        else:
            print("Output mode: Transcription")

        # Preload model
        self.preload_model()

        # Check if one-shot mode
        if self.settings.recording_mode == "one_shot":
            self._run_one_shot()
            return

        print(f"Hotkey: {self.settings.hotkey}")

        # Start hotkey listener
        self.hotkey.start()
        print("Hotkey listener started")

        # Set up signal handlers
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal")
            self._on_quit()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run menu bar app (this blocks)
        print("\nDictation App is ready!")
        print(f"Press {self.settings.hotkey} to start dictating")
        print("Use the menu bar icon to access settings or quit")

        # Show control panel on start if requested
        if getattr(self, '_show_control_panel_on_start', False):
            def _delayed_show():
                import time
                time.sleep(1.0)  # Wait for rumps event loop to start
                self.show_control_panel()
            threading.Thread(target=_delayed_show, daemon=True).start()

        try:
            self.menu_bar.run()
        except KeyboardInterrupt:
            self._on_quit()

    def _run_one_shot(self) -> None:
        """Run in one-shot mode: record once, copy to clipboard, exit."""
        import sys

        print("\n" + "=" * 50)
        print("ONE-SHOT MODE")
        print("=" * 50)
        print(f"Press {self.settings.stop_key.upper()} when done speaking...")
        print("Recording NOW...")
        print("=" * 50 + "\n")

        # Show indicator
        self.indicator.show("listening")

        # Start recording immediately
        self.audio_capture.start()

        # Wait for stop key
        try:
            from pynput import keyboard

            stop_event = threading.Event()
            stop_key = self.settings.stop_key.lower()

            def on_press(key):
                try:
                    if hasattr(key, 'name') and key.name == stop_key:
                        stop_event.set()
                        return False
                    elif hasattr(key, 'char') and key.char == stop_key:
                        stop_event.set()
                        return False
                except AttributeError:
                    pass

            with keyboard.Listener(on_press=on_press) as listener:
                stop_event.wait()

        except KeyboardInterrupt:
            print("\nCancelled by user")
            self.audio_capture.stop()
            self.indicator.hide()
            sys.exit(0)

        # Stop recording
        audio = self.audio_capture.stop()
        print(f"\nRecording stopped. Duration: {len(audio) / 16000:.1f}s")

        # Update UI
        self.indicator.update("processing")
        print("Processing...")

        # Process synchronously in one-shot mode
        self._process_audio_one_shot(audio)

    def _process_audio_one_shot(self, audio) -> None:
        """Process audio in one-shot mode (synchronous).

        Args:
            audio: Audio samples as numpy array
        """
        import sys

        try:
            # Check minimum duration
            if len(audio) < 8000:  # Less than 0.5 seconds
                print("Recording too short!")
                self.indicator.hide()
                sys.exit(1)

            # Transcribe
            print("Transcribing...")
            result = self.whisper.transcribe(audio)

            if not result.text:
                print("No text transcribed")
                self.indicator.hide()
                sys.exit(1)

            print(f"\nDetected language: {result.language}")
            print(f"Raw transcription: {result.text}")

            # Generate or process text based on mode
            if self.generation_enabled and self.drafter:
                print("\nGenerating message from intent...")
                self.indicator.set_text("✨ Drafting...")
                final_text = self.drafter.draft(
                    intent=result.text,
                    context=self._context,
                    language=result.language,
                )
            else:
                final_text = self.processor.process(result.text, result.language)

            print("\n" + "=" * 50)
            print("RESULT (copied to clipboard):")
            print("=" * 50)
            print(final_text)
            print("=" * 50 + "\n")

            # Copy to clipboard
            success = self.inserter.insert(final_text)
            if success:
                self.indicator.update("done")
                self.indicator.set_text("✓ Copied!")
                print("Text copied to clipboard - paste with Cmd+V")
            else:
                self.indicator.update("error")
                print("Failed to copy to clipboard")

            # Brief delay to show success indicator
            time.sleep(1.5)
            self.indicator.hide()

        except Exception as e:
            print(f"Error: {e}")
            self.indicator.update("error")
            self.indicator.set_text(f"❌ Error")
            time.sleep(2)
            self.indicator.hide()
            sys.exit(1)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Local dictation app with Whisper")
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Path to configuration file",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices",
    )
    parser.add_argument(
        "--control-panel",
        action="store_true",
        help="Show control panel window on startup",
    )

    args = parser.parse_args()

    if args.list_devices:
        print("Available audio input devices:")
        devices = AudioCapture.list_devices()
        for d in devices:
            print(f"  [{d['index']}] {d['name']} ({d['channels']} ch)")
        return

    app = DictationApp(config_path=args.config)

    # Show control panel if requested
    if args.control_panel:
        app._show_control_panel_on_start = True
    else:
        app._show_control_panel_on_start = False

    app.run()


if __name__ == "__main__":
    main()
