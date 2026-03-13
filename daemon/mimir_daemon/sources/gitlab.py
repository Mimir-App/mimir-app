"""Fuente de datos GitLab."""

import logging
from typing import Any

import httpx

from .base import VCSSource

logger = logging.getLogger(__name__)


class GitLabSource(VCSSource):
    """Fuente de datos de GitLab API v4."""

    def __init__(self, url: str, token: str) -> None:
        self._base_url = url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/api/v4",
            headers={"PRIVATE-TOKEN": token},
            timeout=15.0,
        )

    async def get_issues(self) -> list[dict[str, Any]]:
        """Obtiene issues asignadas al usuario."""
        issues = []
        page = 1
        while page <= 5:
            resp = await self._client.get(
                "/issues",
                params={
                    "scope": "assigned_to_me",
                    "state": "opened",
                    "per_page": 100,
                    "page": page,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            for item in data:
                item["_type"] = "issue"
                item["project_path"] = item.get("references", {}).get(
                    "full", item.get("web_url", "").split("/-/")[0].split("/")[-2:]
                )
                if isinstance(item["project_path"], list):
                    item["project_path"] = "/".join(item["project_path"])
            issues.extend(data)
            page += 1
        logger.info("GitLab: %d issues obtenidas", len(issues))
        return issues

    async def get_merge_requests(self) -> list[dict[str, Any]]:
        """Obtiene MRs asignadas y para revisar."""
        mrs = []
        for scope in ("assigned_to_me", "reviewer"):
            page = 1
            while page <= 5:
                params: dict[str, Any] = {
                    "state": "opened",
                    "per_page": 100,
                    "page": page,
                }
                if scope == "assigned_to_me":
                    params["scope"] = "assigned_to_me"
                else:
                    params["reviewer_username"] = "me"
                    params["scope"] = "all"

                resp = await self._client.get("/merge_requests", params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    break
                for item in data:
                    item["_type"] = "merge_request"
                    item["project_path"] = item.get("references", {}).get(
                        "full", ""
                    ).split("!")[0].rstrip()
                mrs.extend(data)
                page += 1

        # Deduplicar por ID
        seen = set()
        unique = []
        for mr in mrs:
            if mr["id"] not in seen:
                seen.add(mr["id"])
                unique.append(mr)
        logger.info("GitLab: %d MRs obtenidas", len(unique))
        return unique

    async def close(self) -> None:
        await self._client.aclose()
