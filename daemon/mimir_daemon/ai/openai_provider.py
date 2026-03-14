"""Proveedor de descripciones IA usando OpenAI."""

import logging

import openai

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult
from .gemini import SYSTEM_PROMPT, _build_user_prompt

logger = logging.getLogger(__name__)


class OpenAIProvider(DescriptionProvider):
    """Proveedor de descripciones usando OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con OpenAI."""
        prompt = _build_user_prompt(request)
        logger.debug("OpenAI prompt: %s", prompt)

        response = await self._client.chat.completions.create(
            model=self._model,
            max_tokens=150,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )

        text = (response.choices[0].message.content or "").strip() if response.choices else ""

        if not text:
            logger.warning("OpenAI devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
