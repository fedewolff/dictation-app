"""Voice Activity Detection using Silero VAD."""

from typing import Optional, Tuple

import numpy as np
import torch


class VoiceActivityDetector:
    """Detects voice activity in audio using Silero VAD."""

    def __init__(self, sample_rate: int = 16000, threshold: float = 0.5):
        """Initialize VAD.

        Args:
            sample_rate: Audio sample rate (must be 16000 for Silero)
            threshold: Speech probability threshold (0.0 to 1.0)
        """
        if sample_rate != 16000:
            raise ValueError("Silero VAD requires 16000 Hz sample rate")

        self.sample_rate = sample_rate
        self.threshold = threshold
        self._model = None
        self._utils = None

    def _load_model(self) -> None:
        """Load Silero VAD model lazily."""
        if self._model is not None:
            return

        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
        self._model = model
        self._utils = utils

    def is_speech(self, audio: np.ndarray) -> Tuple[bool, float]:
        """Check if audio chunk contains speech.

        Args:
            audio: Audio samples as numpy array (float32, mono)

        Returns:
            Tuple of (is_speech, confidence)
        """
        self._load_model()

        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).float()

        # Silero expects specific chunk sizes (512, 1024, 1536 samples at 16kHz)
        # For arbitrary audio, we process in chunks
        if len(audio_tensor) < 512:
            return False, 0.0

        # Get speech probability
        speech_prob = self._model(audio_tensor, self.sample_rate).item()

        return speech_prob > self.threshold, speech_prob

    def get_speech_timestamps(
        self,
        audio: np.ndarray,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 500,
    ) -> list:
        """Get timestamps of speech segments in audio.

        Args:
            audio: Audio samples as numpy array
            min_speech_duration_ms: Minimum speech segment duration
            min_silence_duration_ms: Minimum silence to split segments

        Returns:
            List of dicts with 'start' and 'end' sample indices
        """
        self._load_model()

        # Get the utility function
        get_speech_timestamps = self._utils[0]

        audio_tensor = torch.from_numpy(audio).float()

        timestamps = get_speech_timestamps(
            audio_tensor,
            self._model,
            sampling_rate=self.sample_rate,
            min_speech_duration_ms=min_speech_duration_ms,
            min_silence_duration_ms=min_silence_duration_ms,
            threshold=self.threshold,
        )

        return timestamps

    def trim_silence(
        self, audio: np.ndarray, margin_ms: int = 100
    ) -> Tuple[np.ndarray, bool]:
        """Trim silence from beginning and end of audio.

        Args:
            audio: Audio samples as numpy array
            margin_ms: Margin to keep around speech in ms

        Returns:
            Tuple of (trimmed_audio, has_speech)
        """
        timestamps = self.get_speech_timestamps(audio)

        if not timestamps:
            return audio, False

        margin_samples = int(margin_ms * self.sample_rate / 1000)

        start = max(0, timestamps[0]["start"] - margin_samples)
        end = min(len(audio), timestamps[-1]["end"] + margin_samples)

        return audio[start:end], True

    def reset(self) -> None:
        """Reset VAD state (for streaming)."""
        if self._model is not None:
            self._model.reset_states()
