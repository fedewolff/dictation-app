"""Clipboard history management for the dictation app."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict


@dataclass
class HistoryEntry:
    """A single clipboard history entry."""
    text: str
    timestamp: str
    language: Optional[str] = None
    mode: str = "transcription"  # "transcription" or "drafting"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            text=data.get("text", ""),
            timestamp=data.get("timestamp", ""),
            language=data.get("language"),
            mode=data.get("mode", "transcription"),
        )


class ClipboardHistory:
    """Manages clipboard history storage and retrieval."""

    DEFAULT_MAX_ENTRIES = 50

    def __init__(
        self,
        history_path: Optional[str] = None,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ):
        """Initialize clipboard history.

        Args:
            history_path: Path to history JSON file. Uses default if None.
            max_entries: Maximum number of entries to keep.
        """
        self.max_entries = max_entries

        if history_path:
            self._history_path = Path(history_path)
        else:
            # Default to ~/.config/dictation-app/clipboard_history.json
            config_dir = Path.home() / ".config" / "dictation-app"
            config_dir.mkdir(parents=True, exist_ok=True)
            self._history_path = config_dir / "clipboard_history.json"

        self._entries: List[HistoryEntry] = []
        self._load()

    def _load(self) -> None:
        """Load history from file."""
        if not self._history_path.exists():
            self._entries = []
            return

        try:
            with open(self._history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._entries = [
                    HistoryEntry.from_dict(entry)
                    for entry in data.get("entries", [])
                ]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading clipboard history: {e}")
            self._entries = []

    def _save(self) -> None:
        """Save history to file."""
        try:
            data = {
                "version": 1,
                "entries": [entry.to_dict() for entry in self._entries],
            }
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"Error saving clipboard history: {e}")

    def add(
        self,
        text: str,
        language: Optional[str] = None,
        mode: str = "transcription",
    ) -> None:
        """Add a new entry to history.

        Args:
            text: The transcribed/drafted text.
            language: Detected language code.
            mode: "transcription" or "drafting".
        """
        if not text or not text.strip():
            return

        entry = HistoryEntry(
            text=text.strip(),
            timestamp=datetime.now().isoformat(),
            language=language,
            mode=mode,
        )

        # Add to beginning (most recent first)
        self._entries.insert(0, entry)

        # Trim to max entries
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[:self.max_entries]

        self._save()

    def get_all(self) -> List[HistoryEntry]:
        """Get all history entries (most recent first)."""
        return self._entries.copy()

    def get_recent(self, count: int = 10) -> List[HistoryEntry]:
        """Get the most recent N entries.

        Args:
            count: Number of entries to return.
        """
        return self._entries[:count]

    def get_by_index(self, index: int) -> Optional[HistoryEntry]:
        """Get an entry by index (0 = most recent).

        Args:
            index: Index of entry to retrieve.
        """
        if 0 <= index < len(self._entries):
            return self._entries[index]
        return None

    def clear(self) -> None:
        """Clear all history entries."""
        self._entries = []
        self._save()

    def delete(self, index: int) -> bool:
        """Delete an entry by index.

        Args:
            index: Index of entry to delete.

        Returns:
            True if deleted, False if index out of range.
        """
        if 0 <= index < len(self._entries):
            del self._entries[index]
            self._save()
            return True
        return False

    def search(self, query: str) -> List[HistoryEntry]:
        """Search history entries by text content.

        Args:
            query: Search query (case-insensitive).

        Returns:
            Matching entries.
        """
        query_lower = query.lower()
        return [
            entry for entry in self._entries
            if query_lower in entry.text.lower()
        ]

    def __len__(self) -> int:
        """Return number of entries in history."""
        return len(self._entries)

    def __iter__(self):
        """Iterate over history entries."""
        return iter(self._entries)


# Global history instance (singleton pattern)
_history_instance: Optional[ClipboardHistory] = None


def get_history() -> ClipboardHistory:
    """Get the global clipboard history instance."""
    global _history_instance
    if _history_instance is None:
        _history_instance = ClipboardHistory()
    return _history_instance
