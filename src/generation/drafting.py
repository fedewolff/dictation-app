"""Message drafting using LLM to transform spoken intent into professional messages."""

import os
from typing import Optional


class MessageDrafter:
    """Generates professional messages from spoken intent using an LLM."""

    SYSTEM_PROMPT = """You are a professional message drafting assistant. Your task is to take a user's spoken intent or instructions and generate a polished, professional message.

Guidelines:
- Transform the user's description of what they want to say into the actual message
- Match the tone and formality appropriate for the context (colleague, client, etc.)
- Keep the message concise and well-structured
- Do NOT include any meta-commentary or explanations - output ONLY the final message
- If context is provided (like previous email content), incorporate it naturally
- Maintain the user's intended meaning while improving clarity and professionalism
- Use appropriate greetings and sign-offs when relevant

Examples:
- Input: "I want to tell my colleague that the meeting is moved to 3pm"
  Output: "Hi, Just a heads up - the meeting has been moved to 3pm. Let me know if that works for you."

- Input: "tell the client we need more time on the project, maybe a week"
  Output: "I wanted to provide you with an update on the project timeline. After reviewing our progress, we'll need an additional week to ensure we deliver the quality you expect. I'll send over a revised schedule shortly. Please let me know if you have any questions."
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "ollama",
        model: Optional[str] = None,
        ollama_host: Optional[str] = None,
    ):
        """Initialize the message drafter.

        Args:
            api_key: API key for the LLM provider (not needed for Ollama).
            provider: LLM provider - 'ollama', 'openai', or 'anthropic'
            model: Model to use. Defaults to provider's recommended model.
            ollama_host: Ollama server URL (default: http://localhost:11434)
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key()
        self.model = model or self._default_model()
        self.ollama_host = ollama_host or "http://localhost:11434"
        self._client = None

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        if self.provider == "openai":
            return os.environ.get("OPENAI_API_KEY")
        elif self.provider == "anthropic":
            return os.environ.get("ANTHROPIC_API_KEY")
        # Ollama doesn't need an API key
        return None

    def _default_model(self) -> str:
        """Get default model for the provider."""
        if self.provider == "ollama":
            return "llama3.1:8b"  # Best quality for 16GB+ RAM Macs
        elif self.provider == "openai":
            return "gpt-4o-mini"
        elif self.provider == "anthropic":
            return "claude-3-5-haiku-20241022"
        return "llama3.1:8b"

    def _get_client(self):
        """Lazy-load the API client."""
        if self._client is not None:
            return self._client

        if self.provider == "ollama":
            try:
                import ollama
                self._client = ollama.Client(host=self.ollama_host)
            except ImportError:
                raise ImportError("ollama package not installed. Run: pip install ollama")
        elif self.provider == "openai":
            if not self.api_key:
                raise ValueError(
                    "No API key found. Set OPENAI_API_KEY environment variable "
                    "or provide api_key in config."
                )
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError(
                    "No API key found. Set ANTHROPIC_API_KEY environment variable "
                    "or provide api_key in config."
                )
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        return self._client

    def draft(
        self,
        intent: str,
        context: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """Generate a professional message from spoken intent.

        Args:
            intent: The transcribed spoken intent/instructions
            context: Optional context (e.g., previous email content)
            language: Language code for the output (e.g., 'en', 'es')

        Returns:
            The drafted professional message
        """
        client = self._get_client()

        # Build the user message
        user_message = f"Intent: {intent}"
        if context:
            user_message = f"Context:\n{context}\n\n{user_message}"
        if language:
            lang_names = {"en": "English", "es": "Spanish"}
            lang_name = lang_names.get(language, language)
            user_message += f"\n\nPlease write the message in {lang_name}."

        # Call the appropriate API
        if self.provider == "ollama":
            response = client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                options={
                    "temperature": 0.7,
                },
            )
            return response["message"]["content"].strip()

        elif self.provider == "openai":
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=1000,
            )
            return response.choices[0].message.content.strip()

        elif self.provider == "anthropic":
            response = client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_message},
                ],
            )
            return response.content[0].text.strip()

        raise ValueError(f"Unsupported provider: {self.provider}")

    def is_configured(self) -> bool:
        """Check if the drafter is properly configured.

        Returns:
            True if provider is ready to use
        """
        if self.provider == "ollama":
            # Ollama just needs to be running, no API key required
            return True
        return bool(self.api_key)

    def check_ollama_available(self) -> bool:
        """Check if Ollama server is running and model is available.

        Returns:
            True if Ollama is ready
        """
        if self.provider != "ollama":
            return True

        try:
            import ollama
            client = ollama.Client(host=self.ollama_host)
            # Try to list models to check connection
            response = client.list()

            # Handle different response formats from ollama library
            model_names = []
            if isinstance(response, dict):
                model_list = response.get("models", [])
            else:
                model_list = getattr(response, "models", [])

            for m in model_list:
                # Try different attribute names used by ollama library
                name = None
                if isinstance(m, dict):
                    name = m.get("name") or m.get("model", "")
                else:
                    # It's an object - try .name first, then .model
                    name = getattr(m, "name", None) or getattr(m, "model", None) or ""

                if name:
                    # Remove :latest or other tags for comparison
                    base_name = name.split(":")[0]
                    model_names.append(base_name)

            # Compare base names (without tags like :8b or :latest)
            target_base = self.model.split(":")[0]
            if target_base not in model_names:
                print(f"Warning: Model '{self.model}' not found in Ollama.")
                print(f"Available models: {', '.join(model_names) or 'none'}")
                print(f"Run: ollama pull {self.model}")
                return False
            return True
        except Exception as e:
            print(f"Warning: Cannot connect to Ollama at {self.ollama_host}")
            print(f"Error: {e}")
            print("Make sure Ollama is running: ollama serve")
            return False
