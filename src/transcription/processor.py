"""Text post-processing and voice command handling."""

import re
from typing import Dict, Optional


class TextProcessor:
    """Processes transcribed text with voice commands and cleanup."""

    # Default voice commands (bilingual English/Spanish)
    DEFAULT_COMMANDS: Dict[str, str] = {
        # English commands
        "new line": "\n",
        "newline": "\n",
        "new paragraph": "\n\n",
        "period": ".",
        "full stop": ".",
        "comma": ",",
        "question mark": "?",
        "exclamation mark": "!",
        "exclamation point": "!",
        "open quote": '"',
        "close quote": '"',
        "open parenthesis": "(",
        "close parenthesis": ")",
        "colon": ":",
        "semicolon": ";",
        "hyphen": "-",
        "dash": " - ",
        "ellipsis": "...",
        "ampersand": "&",
        "at sign": "@",
        "hashtag": "#",
        "dollar sign": "$",
        "percent sign": "%",
        # Spanish commands
        "nueva linea": "\n",
        "nueva línea": "\n",
        "salto de linea": "\n",
        "salto de línea": "\n",
        "punto y aparte": "\n\n",
        "nuevo parrafo": "\n\n",
        "nuevo párrafo": "\n\n",
        "punto y seguido": ". ",
        "punto": ".",
        "coma": ",",
        "signo de interrogacion": "?",
        "signo de interrogación": "?",
        "signo de exclamacion": "!",
        "signo de exclamación": "!",
        "abrir comillas": '"',
        "cerrar comillas": '"',
        "abrir parentesis": "(",
        "abrir paréntesis": "(",
        "cerrar parentesis": ")",
        "cerrar paréntesis": ")",
        "dos puntos": ":",
        "punto y coma": ";",
        "guion": "-",
        "guión": "-",
        "puntos suspensivos": "...",
        "arroba": "@",
    }

    def __init__(
        self,
        custom_commands: Optional[Dict[str, str]] = None,
        enable_commands: bool = True,
        auto_capitalize: bool = True,
    ):
        """Initialize text processor.

        Args:
            custom_commands: Additional custom voice commands
            enable_commands: Whether to process voice commands
            auto_capitalize: Whether to auto-capitalize after periods
        """
        self.enable_commands = enable_commands
        self.auto_capitalize = auto_capitalize

        # Merge default and custom commands
        self.commands = self.DEFAULT_COMMANDS.copy()
        if custom_commands:
            self.commands.update(custom_commands)

        # Sort commands by length (longest first) to avoid partial matches
        self._sorted_commands = sorted(
            self.commands.keys(), key=len, reverse=True
        )

    def process(self, text: str, language: Optional[str] = None) -> str:
        """Process transcribed text.

        Args:
            text: Raw transcribed text
            language: Detected language code (for language-specific processing)

        Returns:
            Processed text
        """
        if not text:
            return ""

        result = text.strip()

        # Apply voice commands
        if self.enable_commands:
            result = self._apply_commands(result)

        # Clean up whitespace
        result = self._clean_whitespace(result)

        # Auto-capitalize if enabled
        if self.auto_capitalize:
            result = self._auto_capitalize(result)

        return result

    def _apply_commands(self, text: str) -> str:
        """Apply voice commands to text.

        Args:
            text: Input text

        Returns:
            Text with commands replaced
        """
        result = text

        for command in self._sorted_commands:
            replacement = self.commands[command]

            # Case-insensitive replacement
            pattern = re.compile(re.escape(command), re.IGNORECASE)
            result = pattern.sub(replacement, result)

        return result

    def _clean_whitespace(self, text: str) -> str:
        """Clean up whitespace in text.

        Args:
            text: Input text

        Returns:
            Text with cleaned whitespace
        """
        # Remove multiple spaces
        result = re.sub(r" +", " ", text)

        # Remove spaces before punctuation
        result = re.sub(r"\s+([.,;:!?])", r"\1", result)

        # Ensure space after punctuation (except at end or before newline)
        result = re.sub(r"([.,;:!?])([^\s\n])", r"\1 \2", result)

        # Clean up around newlines
        result = re.sub(r" *\n *", "\n", result)
        result = re.sub(r"\n{3,}", "\n\n", result)

        return result.strip()

    def _auto_capitalize(self, text: str) -> str:
        """Auto-capitalize after sentence endings.

        Args:
            text: Input text

        Returns:
            Text with auto-capitalization
        """
        if not text:
            return ""

        # Capitalize first character
        result = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        # Capitalize after sentence endings
        def capitalize_after(match):
            return match.group(1) + match.group(2).upper()

        result = re.sub(r"([.!?]\s+)([a-záéíóúñ])", capitalize_after, result)

        # Capitalize after newlines
        result = re.sub(r"(\n)([a-záéíóúñ])", capitalize_after, result)

        return result

    def add_command(self, trigger: str, replacement: str) -> None:
        """Add a custom voice command.

        Args:
            trigger: Voice trigger phrase
            replacement: Text to replace it with
        """
        self.commands[trigger.lower()] = replacement
        self._sorted_commands = sorted(
            self.commands.keys(), key=len, reverse=True
        )

    def remove_command(self, trigger: str) -> None:
        """Remove a voice command.

        Args:
            trigger: Voice trigger phrase to remove
        """
        trigger_lower = trigger.lower()
        if trigger_lower in self.commands:
            del self.commands[trigger_lower]
            self._sorted_commands = sorted(
                self.commands.keys(), key=len, reverse=True
            )
