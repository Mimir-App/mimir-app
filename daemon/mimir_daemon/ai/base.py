"""Interfaz base para generación de descripciones IA."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DescriptionRequest:
    """Señales de un bloque para generar descripción."""

    app_name: str
    window_title: str
    project_path: str | None
    git_branch: str | None
    git_remote: str | None
    duration_minutes: float


@dataclass
class DescriptionResult:
    """Resultado de generación de descripción."""

    description: str
    confidence: float  # 0.0 - 1.0
    cached: bool = False


class DescriptionProvider(ABC):
    """Interfaz para proveedores de descripciones IA."""

    @abstractmethod
    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        """Genera una descripción para las señales dadas."""
        ...
