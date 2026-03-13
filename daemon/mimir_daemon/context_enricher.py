"""Enriquecimiento de contexto: CWD, git info, SSH config."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EnrichedContext:
    """Contexto enriquecido de un proceso."""

    cwd: str | None = None
    git_branch: str | None = None
    git_remote: str | None = None
    project_path: str | None = None


async def enrich_pid(pid: int) -> EnrichedContext:
    """Enriquece el contexto de un PID activo."""
    ctx = EnrichedContext()

    # Obtener CWD del proceso
    try:
        cwd_link = Path(f"/proc/{pid}/cwd")
        if cwd_link.exists():
            ctx.cwd = str(cwd_link.resolve())
    except (PermissionError, OSError):
        pass

    # Buscar info de git si hay CWD
    if ctx.cwd:
        ctx.git_branch = await _get_git_branch(ctx.cwd)
        ctx.git_remote = await _get_git_remote(ctx.cwd)
        ctx.project_path = _extract_project_path(ctx.cwd)

    return ctx


async def _get_git_branch(cwd: str) -> str | None:
    """Obtiene la rama git actual."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception:
        pass
    return None


async def _get_git_remote(cwd: str) -> str | None:
    """Obtiene la URL del remote origin."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", cwd, "remote", "get-url", "origin",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception:
        pass
    return None


def _extract_project_path(cwd: str) -> str | None:
    """Extrae una ruta de proyecto relativa significativa."""
    path = Path(cwd)
    # Buscar directorio con .git
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return str(parent)
    return cwd
