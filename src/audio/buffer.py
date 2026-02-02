"""Thread-safe audio buffer management."""

import threading
from collections import deque
from typing import Optional

import numpy as np


class AudioBuffer:
    """Thread-safe circular audio buffer."""

    def __init__(self, max_duration_seconds: float = 300.0, sample_rate: int = 16000):
        """Initialize audio buffer.

        Args:
            max_duration_seconds: Maximum audio duration to store
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration_seconds * sample_rate)
        self._buffer: deque = deque(maxlen=self.max_samples)
        self._lock = threading.Lock()

    def append(self, audio_chunk: np.ndarray) -> None:
        """Append audio chunk to buffer.

        Args:
            audio_chunk: Audio samples as numpy array
        """
        with self._lock:
            # Flatten if needed and convert to float32
            samples = audio_chunk.flatten().astype(np.float32)
            self._buffer.extend(samples)

    def get_audio(self) -> np.ndarray:
        """Get all audio from buffer.

        Returns:
            Audio samples as numpy array
        """
        with self._lock:
            return np.array(list(self._buffer), dtype=np.float32)

    def get_last_n_seconds(self, seconds: float) -> np.ndarray:
        """Get last N seconds of audio.

        Args:
            seconds: Number of seconds to retrieve

        Returns:
            Audio samples as numpy array
        """
        n_samples = int(seconds * self.sample_rate)
        with self._lock:
            if len(self._buffer) <= n_samples:
                return np.array(list(self._buffer), dtype=np.float32)
            return np.array(list(self._buffer)[-n_samples:], dtype=np.float32)

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer.clear()

    def __len__(self) -> int:
        """Return number of samples in buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def duration_seconds(self) -> float:
        """Return duration of audio in buffer in seconds."""
        return len(self) / self.sample_rate

    @property
    def is_empty(self) -> bool:
        """Check if buffer is empty."""
        return len(self) == 0
