"""Proveedor de descripciones IA usando Gemini (stub MVP)."""

import hashlib
import logging
from typing import Any

from .base import DescriptionProvider, DescriptionRequest, DescriptionResult

logger = logging.getLogger(__name__)


class GeminiProvider(DescriptionProvider):
    """Proveedor de descripciones usando Google Gemini API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._cache: dict[str, DescriptionResult] = {}

    def _compute_hash(self, request: DescriptionRequest) -> str:
        """Computa hash de las señales para cache."""
        signals = f"{request.app_name}|{request.window_title}|{request.project_path}|{request.git_branch}"
        return hashlib.sha256(signals.encode()).hexdigest()[:16]

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción con Gemini, usando cache por hash de señales."""
        cache_key = self._compute_hash(request)

        if cache_key in self._cache:
            result = self._cache[cache_key]
            return DescriptionResult(
                description=result.description,
                confidence=result.confidence,
                cached=True,
            )

        # TODO: implementar llamada real a Gemini API
        # Por ahora, generar descripción heurística
        description = self._heuristic_description(request)
        result = DescriptionResult(
            description=description,
            confidence=0.5,
            cached=False,
        )

        self._cache[cache_key] = result
        return result

    def _heuristic_description(self, request: DescriptionRequest) -> str:
        """Genera descripción heurística como fallback."""
        parts = []

        if request.git_branch and request.project_path:
            project = request.project_path.split("/")[-1] if "/" in request.project_path else request.project_path
            parts.append(f"Trabajo en {project}")
            if request.git_branch not in ("main", "master"):
                parts.append(f"rama {request.git_branch}")
        elif request.app_name:
            parts.append(f"Usando {request.app_name}")

        if request.window_title:
            title_parts = request.window_title.split(" - ")
            if len(title_parts) > 1:
                parts.append(title_parts[0][:50])

        return " — ".join(parts) if parts else f"Actividad en {request.app_name}"
