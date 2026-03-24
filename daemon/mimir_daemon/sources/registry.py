"""Registro de fuentes de datos."""

import logging
from typing import Any

from .base import VCSSource

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Registro central de fuentes de datos."""

    def __init__(self) -> None:
        self._vcs_sources: dict[str, VCSSource] = {}

    def register_vcs(self, name: str, source: VCSSource) -> None:
        self._vcs_sources[name] = source
        logger.info("Fuente VCS registrada: %s", name)

    def unregister_vcs(self, name: str) -> None:
        """Elimina una fuente VCS del registro."""
        if name in self._vcs_sources:
            del self._vcs_sources[name]
            logger.info("Fuente VCS desregistrada: %s", name)

    def get_gitlab(self) -> "GitLabSource | None":
        """Obtiene la fuente GitLab registrada (o None)."""
        from .gitlab import GitLabSource
        source = self._vcs_sources.get("gitlab")
        return source if isinstance(source, GitLabSource) else None

    def get_github(self) -> "GitHubSource | None":
        """Obtiene la fuente GitHub registrada (o None)."""
        from .github import GitHubSource
        source = self._vcs_sources.get("github")
        return source if isinstance(source, GitHubSource) else None

    def has_source(self, name: str) -> bool:
        """Comprueba si una fuente VCS está registrada."""
        return name in self._vcs_sources

    async def get_all_issues(self) -> list[dict[str, Any]]:
        results = []
        for name, source in self._vcs_sources.items():
            try:
                issues = await source.get_issues()
                results.extend(issues)
            except Exception as e:
                logger.error("Error obteniendo issues de %s: %s", name, e)
        return results

    async def get_all_merge_requests(self) -> list[dict[str, Any]]:
        results = []
        for name, source in self._vcs_sources.items():
            try:
                mrs = await source.get_merge_requests()
                results.extend(mrs)
            except Exception as e:
                logger.error("Error obteniendo MRs de %s: %s", name, e)
        return results
