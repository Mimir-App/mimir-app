"""Servicio orquestador de descripciones IA."""

import hashlib
import logging

from ..db import Database
from .base import DescriptionProvider, DescriptionRequest, DescriptionResult

logger = logging.getLogger(__name__)


class AIService:
    """Orquesta la generación de descripciones IA con cache."""

    def __init__(self, db: Database, provider: DescriptionProvider | None = None) -> None:
        self._db = db
        self._provider = provider
        self.user_role: str = "technical"
        self.user_context: str = ""

    @property
    def provider(self) -> DescriptionProvider | None:
        return self._provider

    @provider.setter
    def provider(self, value: DescriptionProvider | None) -> None:
        self._provider = value

    def _compute_hash(self, request: DescriptionRequest) -> str:
        """Computa hash de las señales para cache."""
        signals = (
            f"{request.app_name}|{request.window_title}|"
            f"{request.project_path}|{request.git_branch}"
        )
        return hashlib.sha256(signals.encode()).hexdigest()[:16]

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera descripción: cache -> provider -> heurístico."""
        cache_key = self._compute_hash(request)

        # 1. Buscar en cache
        cached = await self._db.get_ai_cache(cache_key)
        if cached:
            return DescriptionResult(
                description=cached["description"],
                confidence=cached["confidence"],
                cached=True,
            )

        # 2. Intentar provider
        if self._provider:
            try:
                result = await self._provider.generate(request)
                provider_name = type(self._provider).__name__
                await self._db.set_ai_cache(
                    cache_key, result.description, result.confidence, provider_name
                )
                return result
            except Exception as e:
                logger.error("Error en provider IA: %s", e)

        # 3. Fallback heurístico
        description = self._heuristic(request)
        return DescriptionResult(description=description, confidence=0.5)

    def _heuristic(self, request: DescriptionRequest) -> str:
        """Genera descripción heurística como fallback."""
        parts = []
        if request.git_branch and request.project_path:
            project = request.project_path.rsplit("/", 1)[-1]
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
