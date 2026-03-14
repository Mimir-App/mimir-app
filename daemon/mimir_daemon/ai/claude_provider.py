"""Proveedor de descripciones IA usando Anthropic Claude."""

import logging

import anthropic

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult
from .gemini import SYSTEM_PROMPT, _build_user_prompt

logger = logging.getLogger(__name__)


class ClaudeProvider(DescriptionProvider):
    """Proveedor de descripciones usando Anthropic Claude API."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001") -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con Claude."""
        prompt = _build_user_prompt(request)
        logger.debug("Claude prompt: %s", prompt)

        message = await self._client.messages.create(
            model=self._model,
            max_tokens=150,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        text = (message.content[0].text or "").strip() if message.content else ""

        if not text:
            logger.warning("Claude devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
