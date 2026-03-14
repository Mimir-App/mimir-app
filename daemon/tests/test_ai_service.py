"""Tests para AIService."""

import pytest
import pytest_asyncio

from mimir_daemon.db import Database
from mimir_daemon.ai.service import AIService
from mimir_daemon.ai.base import DescriptionProvider, DescriptionRequest, DescriptionResult


class FakeProvider(DescriptionProvider):
    """Provider falso para tests."""

    def __init__(self, response: str = "Desarrollo en proyecto X", confidence: float = 0.85):
        self.response = response
        self.confidence = confidence
        self.call_count = 0

    async def generate(self, request: DescriptionRequest) -> DescriptionResult:
        self.call_count += 1
        return DescriptionResult(description=self.response, confidence=self.confidence)


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_ai_service_generates_description(db):
    """AIService genera descripción usando el provider."""
    provider = FakeProvider()
    service = AIService(db=db, provider=provider)

    request = DescriptionRequest(
        app_name="code",
        window_title="models.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote="git@github.com:user/mimir.git",
        duration_minutes=45,
    )
    result = await service.generate(request)
    assert result.description == "Desarrollo en proyecto X"
    assert result.confidence == 0.85
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_ai_service_uses_cache(db):
    """AIService devuelve resultado cacheado en la segunda llamada."""
    provider = FakeProvider()
    service = AIService(db=db, provider=provider)

    request = DescriptionRequest(
        app_name="code",
        window_title="models.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=45,
    )
    result1 = await service.generate(request)
    result2 = await service.generate(request)

    assert result1.description == result2.description
    assert result2.cached is True
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_ai_service_fallback_without_provider(db):
    """AIService usa heurístico si no hay provider."""
    service = AIService(db=db, provider=None)

    request = DescriptionRequest(
        app_name="code",
        window_title="server.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=30,
    )
    result = await service.generate(request)
    assert result.description
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_ai_service_handles_provider_error(db):
    """AIService hace fallback si el provider falla."""

    class FailingProvider(DescriptionProvider):
        async def generate(self, request):
            raise RuntimeError("API error")

    service = AIService(db=db, provider=FailingProvider())

    request = DescriptionRequest(
        app_name="firefox",
        window_title="Google — Firefox",
        project_path=None,
        git_branch=None,
        git_remote=None,
        duration_minutes=15,
    )
    result = await service.generate(request)
    assert result.description
    assert result.confidence == 0.5
