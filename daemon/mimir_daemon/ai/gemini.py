"""Proveedor de descripciones IA usando Google Gemini."""

import logging

from google import genai
from google.genai import types

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Genera una descripción concisa (1 línea, máximo 120 caracteres) de la actividad "
    "laboral basándote en las señales proporcionadas. Responde SOLO con la descripción, "
    "sin explicaciones ni formato adicional. Idioma: español."
)


def _build_user_prompt(request: DescriptionRequest) -> str:
    """Construye el prompt de usuario con las señales del bloque."""
    parts = [f"App: {request.app_name}"]
    if request.project_path:
        project = request.project_path.rsplit("/", 1)[-1]
        parts.append(f"Proyecto: {project}")
    if request.git_branch:
        parts.append(f"Rama: {request.git_branch}")
    parts.append(f"Duración: {request.duration_minutes:.0f}min")
    if request.window_titles:
        titles = ", ".join(request.window_titles[:10])
        parts.append(f"Archivos/ventanas: {titles}")
    elif request.window_title:
        parts.append(f"Ventana: {request.window_title}")
    if request.last_commit_message:
        parts.append(f'Último commit: "{request.last_commit_message}"')

    prompt = f"Perfil: {request.user_role}\n"
    if request.user_context:
        prompt += f"Contexto: {request.user_context}\n"
    prompt += "\nSeñales:\n" + "\n".join(f"- {p}" for p in parts)
    return prompt


class GeminiProvider(DescriptionProvider):
    """Proveedor de descripciones usando Google Gemini API."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con Gemini."""
        prompt = _build_user_prompt(request)
        logger.debug("Gemini prompt: %s", prompt)

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        text = (response.text or "").strip()

        if not text:
            logger.warning("Gemini devolvió respuesta vacía")
            return DescriptionResult(
                description=f"Actividad en {request.app_name}",
                confidence=0.3,
            )

        if len(text) > 120:
            text = text[:117] + "..."

        return DescriptionResult(description=text, confidence=0.8)
