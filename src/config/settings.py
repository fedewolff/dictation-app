"""Configuration management for the dictation app."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


class Settings:
    """Manages application settings from YAML config file."""

    DEFAULT_CONFIG = {
        "audio": {
            "input_device": "default",
            "sample_rate": 16000,
        },
        "model": {
            "name": "large-v3",
            "language": "auto",
            "compute_type": "float16",
            "device": "auto",
        },
        "behavior": {
            "mode": "push_to_talk",
            "hotkey": "cmd+shift+space",
            "stop_key": "enter",
            "silence_threshold_ms": 500,
            "play_sounds": True,
            "show_floating_indicator": True,
        },
        "generation": {
            "enabled": True,
            "provider": "ollama",
            "model": "llama3.1:8b",
            "api_key": "",
            "ollama_host": "http://localhost:11434",
        },
        "voice_commands": {
            "enabled": True,
            "custom": {},
        },
        "post_processing": {
            "auto_capitalize": True,
            "auto_punctuate": True,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize settings.

        Args:
            config_path: Path to config file. If None, uses default locations.
        """
        self._config: dict = {}
        self._config_path: Optional[Path] = None

        if config_path:
            self._config_path = Path(config_path)
        else:
            # Check default locations
            locations = [
                Path.home() / ".config" / "dictation-app" / "config.yaml",
                Path(__file__).parent.parent.parent / "config.yaml",
            ]
            for loc in locations:
                if loc.exists():
                    self._config_path = loc
                    break

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file or use defaults."""
        self._config = self.DEFAULT_CONFIG.copy()

        if self._config_path and self._config_path.exists():
            with open(self._config_path, "r") as f:
                file_config = yaml.safe_load(f) or {}
            self._merge_config(self._config, file_config)

    def _merge_config(self, base: dict, override: dict) -> None:
        """Recursively merge override into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation.

        Args:
            key: Config key in dot notation (e.g., 'model.name')
            default: Default value if key not found

        Returns:
            Config value or default
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot notation.

        Args:
            key: Config key in dot notation (e.g., 'model.name')
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def save(self, path: Optional[str] = None) -> None:
        """Save current config to file.

        Args:
            path: Path to save to. Uses current config path if None.
        """
        save_path = Path(path) if path else self._config_path
        if not save_path:
            save_path = Path.home() / ".config" / "dictation-app" / "config.yaml"

        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)

    @property
    def audio_device(self) -> str:
        return self.get("audio.input_device", "default")

    @property
    def sample_rate(self) -> int:
        return self.get("audio.sample_rate", 16000)

    @property
    def model_name(self) -> str:
        return self.get("model.name", "large-v3")

    @property
    def model_language(self) -> Optional[str]:
        lang = self.get("model.language", "auto")
        return None if lang == "auto" else lang

    @property
    def compute_type(self) -> str:
        return self.get("model.compute_type", "float16")

    @property
    def device(self) -> str:
        return self.get("model.device", "auto")

    @property
    def recording_mode(self) -> str:
        return self.get("behavior.mode", "push_to_talk")

    @property
    def hotkey(self) -> str:
        return self.get("behavior.hotkey", "cmd+shift+space")

    @property
    def stop_key(self) -> str:
        return self.get("behavior.stop_key", "enter")

    @property
    def silence_threshold_ms(self) -> int:
        return self.get("behavior.silence_threshold_ms", 500)

    @property
    def play_sounds(self) -> bool:
        return self.get("behavior.play_sounds", True)

    @property
    def show_indicator(self) -> bool:
        return self.get("behavior.show_floating_indicator", True)

    @property
    def voice_commands_enabled(self) -> bool:
        return self.get("voice_commands.enabled", True)

    @property
    def custom_commands(self) -> dict:
        return self.get("voice_commands.custom", {})

    @property
    def generation_enabled(self) -> bool:
        return self.get("generation.enabled", True)

    @property
    def generation_provider(self) -> str:
        return self.get("generation.provider", "openai")

    @property
    def generation_model(self) -> Optional[str]:
        model = self.get("generation.model", "")
        return model if model else None

    @property
    def generation_api_key(self) -> Optional[str]:
        key = self.get("generation.api_key", "")
        return key if key else None

    @property
    def ollama_host(self) -> str:
        return self.get("generation.ollama_host", "http://localhost:11434")

    @property
    def insertion_method(self) -> str:
        return self.get("behavior.insertion_method", "auto")
