from __future__ import annotations

from typing import Any, Protocol

from trans_flow.models import TranslationCommand


class TranslationAgent(Protocol):
    model_name: str

    async def translate(self, command: TranslationCommand) -> str: ...

    async def close(self) -> None: ...


class OllamaTranslationAgent:
    def __init__(self, *, host: str, model: str) -> None:
        # Import lazily so contract/unit tests can inject a fake agent without
        # requiring a running Ollama installation.
        from ollama import AsyncClient

        self._client = AsyncClient(host=host)
        self.model_name = model

    async def translate(self, command: TranslationCommand) -> str:
        glossary = "\n".join(
            f"- {term.source} -> {term.target}" for term in command.glossary
        )
        glossary_instruction = (
            f"\nUse this glossary exactly:\n{glossary}" if glossary else ""
        )
        prompt = (
            f"Translate the source text from {command.source_language} "
            f"to {command.target_language}.\n"
            f"The response must start with exactly this marker: {command.marker}\n"
            "After the marker, output only the complete translation. "
            "Do not add notes, alternatives, or explanations. "
            "Preserve all numbers, URLs, RFC identifiers, code identifiers, "
            "and footnote markers exactly."
            f"{glossary_instruction}\n\n"
            f"SOURCE TEXT:\n{command.source_text}"
        )
        response: Any = await self._client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        message = response.message if hasattr(response, "message") else response["message"]
        content = message.content if hasattr(message, "content") else message["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned an empty translation")
        return content.strip()

    async def close(self) -> None:
        close = getattr(self._client, "close", None)
        if close is not None:
            result = close()
            if result is not None:
                await result
