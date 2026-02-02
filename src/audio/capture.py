"""Audio capture from microphone."""

import threading
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from .buffer import AudioBuffer


class AudioCapture:
    """Captures audio from the microphone."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device: Optional[str] = None,
        chunk_callback: Optional[Callable[[np.ndarray], None]] = None,
    ):
        """Initialize audio capture.

        Args:
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of audio channels (1 for mono)
            device: Audio input device name or None for default
            chunk_callback: Optional callback for each audio chunk
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = self._resolve_device(device)
        self.chunk_callback = chunk_callback

        self._buffer = AudioBuffer(sample_rate=sample_rate)
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._lock = threading.Lock()

    def _resolve_device(self, device: Optional[str]) -> Optional[int]:
        """Resolve device name to device index.

        Args:
            device: Device name or None for default

        Returns:
            Device index or None for default
        """
        if device is None or device == "default":
            return None

        devices = sd.query_devices()
        for i, d in enumerate(devices):
            if device.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                return i

        return None

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Callback for audio stream.

        Args:
            indata: Input audio data
            frames: Number of frames
            time_info: Time information
            status: Stream status
        """
        if status:
            print(f"Audio callback status: {status}")

        # Copy data to avoid issues with buffer reuse
        audio_chunk = indata.copy()

        # Add to buffer
        self._buffer.append(audio_chunk)

        # Call user callback if provided
        if self.chunk_callback:
            self.chunk_callback(audio_chunk)

    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            if self._is_recording:
                return

            self._buffer.clear()
            self._stream = sd.InputStream(
                device=self.device,
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32,
                callback=self._audio_callback,
                blocksize=int(self.sample_rate * 0.03),  # 30ms chunks
            )
            self._stream.start()
            self._is_recording = True

    def stop(self) -> np.ndarray:
        """Stop recording and return captured audio.

        Returns:
            Captured audio as numpy array
        """
        with self._lock:
            if not self._is_recording:
                return np.array([], dtype=np.float32)

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._is_recording = False
            return self._buffer.get_audio()

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    @property
    def duration(self) -> float:
        """Get current recording duration in seconds."""
        return self._buffer.duration_seconds

    @staticmethod
    def list_devices() -> list:
        """List available audio input devices.

        Returns:
            List of device info dictionaries
        """
        devices = sd.query_devices()
        input_devices = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                input_devices.append(
                    {
                        "index": i,
                        "name": d["name"],
                        "channels": d["max_input_channels"],
                        "sample_rate": d["default_samplerate"],
                    }
                )
        return input_devices
