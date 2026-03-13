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
