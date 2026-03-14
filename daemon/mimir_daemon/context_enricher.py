"""Enriquecimiento de contexto: CWD, git info, SSH config."""

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache de git info para evitar llamadas repetidas al mismo directorio
_git_cache: dict[str, tuple[str | None, str | None]] = {}
_GIT_CACHE_MAX = 50


@dataclass
class EnrichedContext:
    """Contexto enriquecido de un proceso."""

    cwd: str | None = None
    git_branch: str | None = None
    git_remote: str | None = None
    project_path: str | None = None
    ssh_host: str | None = None
    last_commit_message: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


async def enrich_pid(pid: int) -> EnrichedContext:
    """Enriquece el contexto de un PID activo."""
    ctx = EnrichedContext()

    # Obtener CWD del proceso directamente desde /proc
    ctx.cwd = _read_proc_cwd(pid)

    # Detectar sesion SSH
    ctx.ssh_host = _detect_ssh_session(pid)

    # Buscar info de git si hay CWD
    if ctx.cwd:
        git_root = _find_git_root(ctx.cwd)
        if git_root:
            ctx.project_path = str(git_root)
            branch, remote = await _get_git_info(str(git_root))
            ctx.git_branch = branch
            ctx.git_remote = remote
            ctx.last_commit_message = await _get_last_commit_message(str(git_root))
        else:
            ctx.project_path = ctx.cwd

    return ctx


def _read_proc_cwd(pid: int) -> str | None:
    """Lee el CWD de un proceso desde /proc."""
    try:
        cwd_link = Path(f"/proc/{pid}/cwd")
        if cwd_link.exists():
            return str(cwd_link.resolve())
    except (PermissionError, OSError):
        pass
    return None


def _detect_ssh_session(pid: int) -> str | None:
    """Detecta si el proceso es una sesion SSH y extrae el host."""
    try:
        cmdline_path = Path(f"/proc/{pid}/cmdline")
        if not cmdline_path.exists():
            return None
        parts = cmdline_path.read_bytes().split(b"\x00")
        parts = [p.decode(errors="replace") for p in parts if p]
        # Buscar patron ssh <host>
        for i, part in enumerate(parts):
            if part.endswith("/ssh") or part == "ssh":
                # El host suele ser el ultimo argumento no-flag
                for arg in reversed(parts[i + 1:]):
                    if not arg.startswith("-"):
                        return _resolve_ssh_alias(arg)
    except (PermissionError, OSError):
        pass
    return None


def _resolve_ssh_alias(host: str) -> str:
    """Resuelve un alias SSH a su hostname real desde ~/.ssh/config."""
    ssh_config = Path.home() / ".ssh" / "config"
    if not ssh_config.exists():
        return host
    try:
        current_host = None
        for line in ssh_config.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("host "):
                current_host = stripped.split(None, 1)[1].strip()
            elif stripped.lower().startswith("hostname ") and current_host:
                if current_host == host:
                    return stripped.split(None, 1)[1].strip()
    except (OSError, UnicodeDecodeError):
        pass
    return host


def _find_git_root(cwd: str) -> Path | None:
    """Busca la raiz del repositorio git subiendo directorios."""
    path = Path(cwd)
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
        # No subir mas alla de home
        if parent == Path.home():
            break
    return None


async def _get_git_info(git_root: str) -> tuple[str | None, str | None]:
    """Obtiene rama y remote de un repo git. Usa cache."""
    if git_root in _git_cache:
        return _git_cache[git_root]

    branch = await _run_git(git_root, "rev-parse", "--abbrev-ref", "HEAD")
    remote = await _run_git(git_root, "remote", "get-url", "origin")

    # Limpiar cache si crece mucho
    if len(_git_cache) >= _GIT_CACHE_MAX:
        _git_cache.clear()

    _git_cache[git_root] = (branch, remote)
    return branch, remote


async def _get_last_commit_message(git_root: str) -> str | None:
    """Obtiene el mensaje del último commit."""
    return await _run_git(git_root, "log", "-1", "--format=%s")


async def _run_git(cwd: str, *args: str) -> str | None:
    """Ejecuta un comando git y devuelve el resultado."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", cwd, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
        if proc.returncode == 0:
            return stdout.decode().strip()
    except (asyncio.TimeoutError, Exception):
        pass
    return None


def invalidate_git_cache() -> None:
    """Limpia la cache de git (util para tests)."""
    _git_cache.clear()
