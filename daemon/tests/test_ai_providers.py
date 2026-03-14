"""Tests para providers IA (con mocks de SDKs)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mimir_daemon.ai.base import DescriptionRequest


def _make_request(**overrides) -> DescriptionRequest:
    defaults = dict(
        app_name="code",
        window_title="server.py — VS Code",
        project_path="/home/user/mimir-app",
        git_branch="feat/ai",
        git_remote=None,
        duration_minutes=45,
        window_titles=["server.py — VS Code", "test_server.py — VS Code"],
        last_commit_message="fix: retry logic",
        user_role="technical",
        user_context="Backend developer",
    )
    defaults.update(overrides)
    return DescriptionRequest(**defaults)


@pytest.mark.asyncio
async def test_gemini_provider_builds_prompt_and_calls_api():
    """GeminiProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.gemini import GeminiProvider

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Desarrollo de lógica de reintento en servidor"
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Desarrollo de lógica de reintento en servidor"
    assert result.confidence == 0.8
    mock_model.generate_content_async.assert_called_once()
    call_args = mock_model.generate_content_async.call_args[0][0]
    assert "server.py" in call_args
    assert "feat/ai" in call_args
    assert "technical" in call_args


@pytest.mark.asyncio
async def test_claude_provider_builds_prompt_and_calls_api():
    """ClaudeProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.claude_provider import ClaudeProvider

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="Implementación de reintentos en API")]
    mock_client.messages = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("mimir_daemon.ai.claude_provider.anthropic.AsyncAnthropic", return_value=mock_client):
        provider = ClaudeProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Implementación de reintentos en API"
    assert result.confidence == 0.8
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_openai_provider_builds_prompt_and_calls_api():
    """OpenAIProvider construye prompt correcto y llama a la API."""
    from mimir_daemon.ai.openai_provider import OpenAIProvider

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "Corrección de lógica de sincronización"
    mock_response.choices = [mock_choice]
    mock_client.chat = MagicMock()
    mock_client.chat.completions = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.openai_provider.openai.AsyncOpenAI", return_value=mock_client):
        provider = OpenAIProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description == "Corrección de lógica de sincronización"
    assert result.confidence == 0.8
    mock_client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_gemini_provider_handles_empty_response():
    """GeminiProvider maneja respuesta vacía."""
    from mimir_daemon.ai.gemini import GeminiProvider

    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)

    with patch("mimir_daemon.ai.gemini.genai") as mock_genai:
        mock_genai.GenerativeModel.return_value = mock_model
        provider = GeminiProvider(api_key="test-key")
        result = await provider.generate(_make_request())

    assert result.description
    assert result.confidence < 0.8
