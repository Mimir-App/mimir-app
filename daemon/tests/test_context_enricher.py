"""Tests para context_enricher."""

import os
import pytest
from pathlib import Path

from mimir_daemon.context_enricher import (
    EnrichedContext,
    _find_git_root,
    _resolve_ssh_alias,
    invalidate_git_cache,
)


def test_find_git_root_in_repo(tmp_path):
    """Encuentra la raiz de un repo git."""
    git_dir = tmp_path / "myrepo" / ".git"
    git_dir.mkdir(parents=True)
    subdir = tmp_path / "myrepo" / "src" / "lib"
    subdir.mkdir(parents=True)

    result = _find_git_root(str(subdir))
    assert result == tmp_path / "myrepo"


def test_find_git_root_no_repo(tmp_path):
    """Devuelve None si no hay repo git."""
    plain_dir = tmp_path / "no_repo"
    plain_dir.mkdir()

    result = _find_git_root(str(plain_dir))
    assert result is None


def test_resolve_ssh_alias_no_config(tmp_path, monkeypatch):
    """Sin ~/.ssh/config devuelve el host tal cual."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert _resolve_ssh_alias("myserver") == "myserver"


def test_resolve_ssh_alias_with_config(tmp_path, monkeypatch):
    """Resuelve alias desde ~/.ssh/config."""
    ssh_dir = tmp_path / ".ssh"
    ssh_dir.mkdir()
    config = ssh_dir / "config"
    config.write_text(
        "Host prod\n"
        "    HostName 10.0.0.1\n"
        "    User deploy\n"
        "\n"
        "Host staging\n"
        "    HostName 10.0.0.2\n"
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert _resolve_ssh_alias("prod") == "10.0.0.1"
    assert _resolve_ssh_alias("staging") == "10.0.0.2"
    assert _resolve_ssh_alias("unknown") == "unknown"


def test_enriched_context_defaults():
    """EnrichedContext tiene todos los campos a None por defecto."""
    ctx = EnrichedContext()
    assert ctx.cwd is None
    assert ctx.git_branch is None
    assert ctx.git_remote is None
    assert ctx.project_path is None
    assert ctx.ssh_host is None
    assert ctx.extra == {}


def test_invalidate_git_cache():
    """invalidate_git_cache limpia la cache sin error."""
    invalidate_git_cache()  # No deberia lanzar excepcion
