"""Fuente de datos GitLab."""

import asyncio
import logging
from typing import Any

import httpx

from .base import VCSSource

logger = logging.getLogger(__name__)


def _normalize_milestone(item: dict) -> None:
    """Extrae el titulo del milestone si viene como objeto JSON."""
    ms = item.get("milestone")
    if isinstance(ms, dict):
        item["milestone"] = ms.get("title")


def _normalize_mr_pipeline(item: dict) -> None:
    """Extrae pipeline status, approved_by y has_conflicts de un MR de GitLab."""
    # Pipeline
    pipeline = item.get("head_pipeline")
    if isinstance(pipeline, dict):
        item["pipeline_status"] = pipeline.get("status")
        item["pipeline_web_url"] = pipeline.get("web_url")
    else:
        item["pipeline_status"] = None
        item["pipeline_web_url"] = None
    # Aprobaciones
    approved = item.get("approved_by", [])
    item["approved_by"] = [
        a.get("user", {}).get("username", "") if isinstance(a, dict) else ""
        for a in (approved if isinstance(approved, list) else [])
    ]
    # has_conflicts ya viene directo de la API de GitLab


class GitLabSource(VCSSource):
    """Fuente de datos de GitLab API v4."""

    def __init__(self, url: str, token: str) -> None:
        self._base_url = url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/api/v4",
            headers={"PRIVATE-TOKEN": token},
            timeout=15.0,
        )
        self._username: str | None = None

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
                item["_source"] = "gitlab"
                ref = item.get("references", {}).get(
                    "full", item.get("web_url", "").split("/-/")[0].split("/")[-2:]
                )
                if isinstance(ref, list):
                    ref = "/".join(ref)
                # Strip #iid del final (references.full = "group/project#123")
                item["project_path"] = ref.rsplit("#", 1)[0] if "#" in ref else ref
                _normalize_milestone(item)
            issues.extend(data)
            page += 1
        logger.info("GitLab: %d issues obtenidas", len(issues))
        return issues

    async def _get_username(self) -> str:
        """Obtiene y cachea el username del usuario autenticado."""
        if not self._username:
            user = await self.get_current_user()
            self._username = user.get("username", "")
        return self._username

    async def get_merge_requests(self) -> list[dict[str, Any]]:
        """Obtiene MRs asignadas y para revisar."""
        username = await self._get_username()
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
                    if not username:
                        break
                    params["reviewer_username"] = username
                    params["scope"] = "all"

                resp = await self._client.get("/merge_requests", params=params)
                resp.raise_for_status()
                data = resp.json()
                if not data:
                    break
                for item in data:
                    item["_type"] = "merge_request"
                    item["_source"] = "gitlab"
                    item["project_path"] = item.get("references", {}).get(
                        "full", ""
                    ).split("!")[0].rstrip()
                    _normalize_milestone(item)
                mrs.extend(data)
                page += 1

        # Deduplicar por ID
        seen = set()
        unique = []
        for mr in mrs:
            if mr["id"] not in seen:
                seen.add(mr["id"])
                unique.append(mr)

        # Enriquecer con pipeline, aprobaciones y conflictos
        await self._enrich_mrs(unique)

        logger.info("GitLab: %d MRs obtenidas", len(unique))
        return unique

    async def _enrich_mrs(self, mrs: list[dict[str, Any]]) -> None:
        """Enriquece MRs con head_pipeline, approved_by y has_conflicts."""

        async def _enrich_one(mr: dict) -> None:
            gid = mr.get("id")
            if not gid:
                return
            try:
                resp = await self._client.get(f"/merge_requests/{gid}")
                if resp.status_code == 200:
                    full = resp.json()
                    mr["head_pipeline"] = full.get("head_pipeline")
                    mr["approved_by"] = full.get("approved_by", [])
                    mr["has_conflicts"] = full.get("has_conflicts", False)
            except Exception as e:
                logger.debug("Error enriqueciendo MR %s: %s", gid, e)
            _normalize_mr_pipeline(mr)

        semaphore = asyncio.Semaphore(10)

        async def _limited(mr: dict) -> None:
            async with semaphore:
                await _enrich_one(mr)

        await asyncio.gather(*[_limited(mr) for mr in mrs])

    async def search_issues(self, query: str, per_page: int = 20) -> list[dict]:
        """Busca issues en todos los proyectos accesibles."""
        try:
            resp = await self._client.get(
                "/issues",
                params={"search": query, "scope": "all", "state": "opened", "per_page": per_page},
            )
            resp.raise_for_status()
            issues = resp.json()
            for issue in issues:
                issue["_source"] = "gitlab"
                ref = issue.get("references", {}).get("full", "")
                issue["project_path"] = ref.rsplit("#", 1)[0] if "#" in ref else ""
                _normalize_milestone(issue)
            return issues
        except Exception as e:
            logger.error("Error buscando issues en GitLab: %s", e)
            return []

    async def get_issue_notes(
        self, project_id: str, issue_iid: int, per_page: int = 5
    ) -> list[dict]:
        """Obtiene notas de usuario de una issue (excluye system notes)."""
        try:
            resp = await self._client.get(
                f"/projects/{project_id}/issues/{issue_iid}/notes",
                params={"sort": "desc", "per_page": per_page * 2},
            )
            resp.raise_for_status()
            notes = [n for n in resp.json() if not n.get("system", False)]
            return notes[:per_page]
        except Exception as e:
            logger.error("Error obteniendo notas de issue %s#%d: %s", project_id, issue_iid, e)
            return []

    async def get_issues_by_ids(self, issue_ids: list[int]) -> list[dict]:
        """Obtiene issues por sus IDs globales."""
        if not issue_ids:
            return []
        results = []
        for gid in issue_ids:
            try:
                resp = await self._client.get(f"/issues/{gid}")
                if resp.status_code == 200:
                    issue = resp.json()
                    issue["_type"] = "issue"
                    issue["_source"] = "gitlab"
                    ref = issue.get("references", {}).get("full", "")
                    issue["project_path"] = ref.rsplit("#", 1)[0] if "#" in ref else ""
                    _normalize_milestone(issue)
                    results.append(issue)
                else:
                    logger.debug("GitLab issue %d: status %d", gid, resp.status_code)
            except Exception as e:
                logger.debug("Error obteniendo issue %d: %s", gid, e)
                continue
        return results

    async def search_merge_requests(self, query: str, per_page: int = 20) -> list[dict]:
        """Busca merge requests en todos los proyectos accesibles."""
        try:
            resp = await self._client.get(
                "/merge_requests",
                params={"search": query, "scope": "all", "state": "opened", "per_page": per_page},
            )
            resp.raise_for_status()
            mrs = resp.json()
            for mr in mrs:
                mr["_source"] = "gitlab"
                ref = mr.get("references", {}).get("full", "")
                mr["project_path"] = ref.split("!")[0].rstrip() if "!" in ref else ""
                _normalize_milestone(mr)
                _normalize_mr_pipeline(mr)
            return mrs
        except Exception as e:
            logger.error("Error buscando merge requests en GitLab: %s", e)
            return []

    async def get_mr_notes(
        self, project_id: str, mr_iid: int, per_page: int = 5
    ) -> list[dict]:
        """Obtiene notas de usuario de un MR (excluye system notes)."""
        try:
            resp = await self._client.get(
                f"/projects/{project_id}/merge_requests/{mr_iid}/notes",
                params={"sort": "desc", "per_page": per_page * 2},
            )
            resp.raise_for_status()
            notes = [n for n in resp.json() if not n.get("system", False)]
            return notes[:per_page]
        except Exception as e:
            logger.error("Error obteniendo notas de MR %s!%d: %s", project_id, mr_iid, e)
            return []

    async def get_mr_conflicts(self, project_id: str, mr_iid: int) -> list[dict]:
        """Obtiene archivos en conflicto de un MR."""
        try:
            resp = await self._client.get(
                f"/projects/{project_id}/merge_requests/{mr_iid}/changes",
            )
            resp.raise_for_status()
            data = resp.json()
            diffs = data.get("changes", data.get("diffs", []))
            conflicts = []
            for diff in diffs:
                if diff.get("conflict") or diff.get("has_conflict"):
                    conflicts.append({
                        "old_path": diff.get("old_path"),
                        "new_path": diff.get("new_path"),
                        "conflict": True,
                    })
            return conflicts
        except Exception as e:
            logger.error("Error obteniendo conflictos de MR %s!%d: %s", project_id, mr_iid, e)
            return []

    async def get_merge_requests_by_ids(self, mr_ids: list[int]) -> list[dict]:
        """Obtiene MRs por sus IDs globales."""
        if not mr_ids:
            return []
        results = []
        for gid in mr_ids:
            try:
                resp = await self._client.get(f"/merge_requests/{gid}")
                if resp.status_code == 200:
                    mr = resp.json()
                    mr["_type"] = "merge_request"
                    mr["_source"] = "gitlab"
                    ref = mr.get("references", {}).get("full", "")
                    mr["project_path"] = ref.split("!")[0].rstrip() if "!" in ref else ""
                    _normalize_milestone(mr)
                    _normalize_mr_pipeline(mr)
                    results.append(mr)
            except Exception:
                continue
        return results

    async def get_todos(self) -> list[dict]:
        """Obtiene TODOs del usuario."""
        try:
            resp = await self._client.get(
                "/todos",
                params={"state": "pending", "per_page": 50},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Error obteniendo TODOs de GitLab: %s", e)
            return []

    async def get_current_user(self) -> dict:
        """Obtiene info del usuario actual."""
        try:
            resp = await self._client.get("/user")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error("Error obteniendo usuario actual de GitLab: %s", e)
            return {}

    async def get_labels(self, project_paths: list[str] | None = None) -> list[dict]:
        """Obtiene labels unicas de los proyectos del usuario."""
        try:
            seen: set[str] = set()
            labels = []
            if not project_paths:
                issues = await self.get_issues()
                project_paths = list({i["project_path"] for i in issues})

            for path in project_paths:
                encoded = path.replace("/", "%2F")
                try:
                    resp = await self._client.get(
                        f"/projects/{encoded}/labels",
                        params={"per_page": 100},
                    )
                    if resp.status_code == 200:
                        for label in resp.json():
                            name = label["name"]
                            if name not in seen:
                                seen.add(name)
                                labels.append({"name": name, "color": label.get("color", "")})
                except Exception:
                    continue
            return sorted(labels, key=lambda l: l["name"])
        except Exception as e:
            logger.error("Error obteniendo labels de GitLab: %s", e)
            return []

    async def close(self) -> None:
        await self._client.aclose()
