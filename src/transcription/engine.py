"""Whisper transcription engine using faster-whisper."""

from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

import numpy as np
from faster_whisper import WhisperModel


@dataclass
class TranscriptionResult:
    """Result of transcription."""

    text: str
    language: str
    language_probability: float
    segments: list


class WhisperEngine:
    """Whisper-based speech recognition engine."""

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "auto",
        compute_type: str = "float16",
        language: Optional[str] = None,
    ):
        """Initialize Whisper engine.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large-v3)
            device: Device to use (auto, cpu, cuda, mps)
            compute_type: Compute type (float32, float16, int8)
            language: Language code or None for auto-detection
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: Optional[WhisperModel] = None

    def _load_model(self) -> None:
        """Load Whisper model lazily."""
        if self._model is not None:
            return

        print(f"Loading Whisper model: {self.model_name}...")

        # Determine device
        device = self.device
        compute_type = self.compute_type

        if device == "auto":
            # Check for MPS (Apple Silicon) or CUDA
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
                else:
                    device = "cpu"
            except ImportError:
                device = "cpu"

        # Adjust compute_type for CPU (float16 not supported efficiently)
        if device == "cpu" and compute_type == "float16":
            compute_type = "int8"  # Best performance on CPU
            print(f"Using int8 compute type for CPU (faster than float32)")

        self._model = WhisperModel(
            self.model_name,
            device=device,
            compute_type=compute_type,
        )
        print(f"Model loaded on {device} with {compute_type}")

    def transcribe(
        self,
        audio: np.ndarray,
        vad_filter: bool = True,
        vad_parameters: Optional[dict] = None,
    ) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Audio samples as numpy array (float32, 16kHz, mono)
            vad_filter: Whether to use VAD filtering
            vad_parameters: VAD parameters dict

        Returns:
            TranscriptionResult with text and metadata
        """
        self._load_model()

        if vad_parameters is None:
            vad_parameters = {
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            }

        segments, info = self._model.transcribe(
            audio,
            language=self.language,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters,
            beam_size=5,
            best_of=5,
            temperature=0.0,
        )

        # Collect all segments
        segment_list = []
        text_parts = []

        for segment in segments:
            segment_list.append(
                {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "avg_logprob": segment.avg_logprob,
                }
            )
            text_parts.append(segment.text)

        full_text = "".join(text_parts).strip()

        return TranscriptionResult(
            text=full_text,
            language=info.language,
            language_probability=info.language_probability,
            segments=segment_list,
        )

    def transcribe_stream(
        self, audio: np.ndarray, chunk_duration: float = 5.0
    ) -> Iterator[Tuple[str, str]]:
        """Transcribe audio in streaming fashion.

        Args:
            audio: Audio samples as numpy array
            chunk_duration: Duration of each chunk in seconds

        Yields:
            Tuples of (partial_text, detected_language)
        """
        self._load_model()

        sample_rate = 16000
        chunk_size = int(chunk_duration * sample_rate)

        for i in range(0, len(audio), chunk_size):
            chunk = audio[i : i + chunk_size]
            if len(chunk) < sample_rate:  # Skip chunks < 1 second
                continue

            result = self.transcribe(chunk, vad_filter=False)
            yield result.text, result.language

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None

    def preload(self) -> None:
        """Preload the model."""
        self._load_model()
