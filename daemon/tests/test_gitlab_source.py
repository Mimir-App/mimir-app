"""Tests para GitLabSource con mock de httpx."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import httpx

from mimir_daemon.sources.gitlab import GitLabSource


def _mock_response(data, status_code=200):
    """Crea una respuesta httpx mock."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_get_issues_returns_parsed_data():
    """get_issues devuelve issues con project_path."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    mock_data = [
        {
            "id": 1, "iid": 42, "title": "Fix bug",
            "state": "opened", "web_url": "https://gitlab.test/group/project/-/issues/42",
            "references": {"full": "group/project#42"},
            "labels": ["bug"], "assignees": [],
            "milestone": None, "due_date": None,
            "created_at": "2026-03-01T10:00:00Z",
            "updated_at": "2026-03-13T15:00:00Z",
            "user_notes_count": 2,
        }
    ]

    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response(mock_data),
        _mock_response([]),
    ])

    issues = await source.get_issues()
    assert len(issues) == 1
    assert issues[0]["title"] == "Fix bug"
    assert issues[0]["_type"] == "issue"


@pytest.mark.asyncio
async def test_get_merge_requests_deduplicates():
    """get_merge_requests deduplica MRs que aparecen en ambos scopes."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    mr = {
        "id": 10, "iid": 7, "title": "feat: auth",
        "state": "opened", "web_url": "https://gitlab.test/group/project/-/merge_requests/7",
        "references": {"full": "group/project!7"},
        "labels": [], "assignees": [], "reviewers": [],
        "source_branch": "feat/auth", "target_branch": "main",
        "has_conflicts": False, "pipeline_status": "success",
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-13T12:00:00Z",
        "user_notes_count": 1,
    }

    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response([mr]),    # assigned_to_me page 1
        _mock_response([]),      # assigned_to_me page 2
        _mock_response([mr]),    # reviewer page 1 (same MR)
        _mock_response([]),      # reviewer page 2
    ])

    mrs = await source.get_merge_requests()
    assert len(mrs) == 1  # Deduplicado


@pytest.mark.asyncio
async def test_get_issues_handles_error():
    """get_issues propaga error si la API falla."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response([], status_code=401),
    ])

    with pytest.raises(httpx.HTTPStatusError):
        await source.get_issues()


@pytest.mark.asyncio
async def test_get_issues_empty():
    """get_issues devuelve lista vacía si no hay issues."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    source._client = MagicMock()
    source._client.get = AsyncMock(return_value=_mock_response([]))

    issues = await source.get_issues()
    assert issues == []
