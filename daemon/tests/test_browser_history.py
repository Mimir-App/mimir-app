"""Tests para el módulo de historial de navegador."""

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mimir_daemon.browser_history import (
    _CHROME_EPOCH_OFFSET,
    _datetime_to_chrome_us,
    _extract_domain,
    _group_by_domain,
    detect_browsers,
    get_history_for_date,
    read_chromium_history,
    read_firefox_history,
)


# --- Helpers ---


def _create_chrome_db(db_path: str, visits: list[tuple]) -> None:
    """Crea una DB Chrome con schema mínimo e inserta visitas.

    visits: [(url, title, visit_time_us), ...]
    """
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url LONGVARCHAR,
            title LONGVARCHAR,
            visit_count INTEGER DEFAULT 0,
            last_visit_time INTEGER DEFAULT 0,
            hidden INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url INTEGER,
            visit_time INTEGER,
            from_visit INTEGER DEFAULT 0,
            transition INTEGER DEFAULT 0,
            visit_duration INTEGER DEFAULT 0
        )
    """)
    for url, title, visit_time in visits:
        conn.execute("INSERT INTO urls (url, title) VALUES (?, ?)", (url, title))
        url_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO visits (url, visit_time) VALUES (?, ?)",
            (url_id, visit_time),
        )
    conn.commit()
    conn.close()


def _create_firefox_db(db_path: str, visits: list[tuple]) -> None:
    """Crea una DB Firefox con schema mínimo e inserta visitas.

    visits: [(url, title, visit_date_us), ...]
    """
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE moz_places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            title TEXT,
            visit_count INTEGER DEFAULT 0,
            last_visit_date INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE moz_historyvisits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id INTEGER,
            visit_date INTEGER,
            visit_type INTEGER DEFAULT 1
        )
    """)
    for url, title, visit_date in visits:
        conn.execute("INSERT INTO moz_places (url, title) VALUES (?, ?)", (url, title))
        place_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT INTO moz_historyvisits (place_id, visit_date) VALUES (?, ?)",
            (place_id, visit_date),
        )
    conn.commit()
    conn.close()


def _chrome_ts(hour: int, minute: int = 0, date: str = "2026-03-27") -> int:
    """Genera timestamp Chrome para una hora en una fecha."""
    dt = datetime.strptime(f"{date} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
    return _datetime_to_chrome_us(dt)


def _unix_us(hour: int, minute: int = 0, date: str = "2026-03-27") -> int:
    """Genera timestamp Unix microsegundos para una hora en una fecha."""
    dt = datetime.strptime(f"{date} {hour:02d}:{minute:02d}", "%Y-%m-%d %H:%M")
    return int(dt.timestamp()) * 1_000_000


# --- detect_browsers ---


def test_detect_browsers_none(tmp_path):
    """Lista vacía si no hay DBs en las rutas."""
    with patch("mimir_daemon.browser_history.BROWSER_PROFILES", {"chrome": str(tmp_path / "no-existe")}):
        result = detect_browsers()
    assert result == []


def test_detect_browsers_chrome(tmp_path):
    """Detecta Chrome si la DB existe."""
    db_file = tmp_path / "History"
    db_file.touch()
    with patch("mimir_daemon.browser_history.BROWSER_PROFILES", {"chrome": str(db_file)}):
        result = detect_browsers()
    assert len(result) == 1
    assert result[0]["name"] == "chrome"
    assert result[0]["path"] == str(db_file)


def test_detect_browsers_firefox_glob(tmp_path):
    """Detecta Firefox con glob del perfil."""
    profile_dir = tmp_path / "abc123.default-release"
    profile_dir.mkdir()
    (profile_dir / "places.sqlite").touch()
    pattern = str(tmp_path / "*.default-release" / "places.sqlite")
    with patch("mimir_daemon.browser_history.BROWSER_PROFILES", {"firefox": pattern}):
        result = detect_browsers()
    assert len(result) == 1
    assert result[0]["name"] == "firefox"


# --- _extract_domain ---


def test_extract_domain_http():
    assert _extract_domain("https://github.com/org/repo") == "github.com"


def test_extract_domain_strips_www():
    assert _extract_domain("https://www.google.com/search") == "google.com"


def test_extract_domain_ignores_chrome_internal():
    assert _extract_domain("chrome://settings") is None


def test_extract_domain_ignores_empty():
    assert _extract_domain("") is None


# --- read_chromium_history ---


def test_read_chromium_history(tmp_path):
    """Lee visitas de Chrome para una fecha específica."""
    db_path = str(tmp_path / "History")
    _create_chrome_db(db_path, [
        ("https://github.com/pulls", "Pull Requests", _chrome_ts(9, 30)),
        ("https://github.com/issues", "Issues", _chrome_ts(10, 0)),
        ("https://stackoverflow.com/q/123", "Python async", _chrome_ts(10, 15)),
        # Fuera de rango (día anterior)
        ("https://google.com", "Google", _chrome_ts(12, 0, "2026-03-26")),
    ])
    result = read_chromium_history(db_path, "2026-03-27")
    assert len(result) == 2  # github.com + stackoverflow.com

    github = next(d for d in result if d["domain"] == "github.com")
    assert github["visits"] == 2
    assert github["from"] == "09:30"
    assert github["to"] == "10:00"
    assert len(github["titles"]) == 2


def test_read_chromium_history_empty(tmp_path):
    """Retorna lista vacía si no hay visitas para la fecha."""
    db_path = str(tmp_path / "History")
    _create_chrome_db(db_path, [
        ("https://github.com", "GitHub", _chrome_ts(12, 0, "2026-03-26")),
    ])
    result = read_chromium_history(db_path, "2026-03-27")
    assert result == []


def test_read_chromium_history_missing_db():
    """Retorna lista vacía si la DB no existe."""
    result = read_chromium_history("/tmp/no-existe-12345.db", "2026-03-27")
    assert result == []


# --- read_firefox_history ---


def test_read_firefox_history(tmp_path):
    """Lee visitas de Firefox para una fecha específica."""
    db_path = str(tmp_path / "places.sqlite")
    _create_firefox_db(db_path, [
        ("https://docs.python.org/3/", "Python Docs", _unix_us(11, 0)),
        ("https://docs.python.org/3/library/", "Library", _unix_us(11, 30)),
        ("https://mdn.io/fetch", "Fetch API", _unix_us(14, 0)),
    ])
    result = read_firefox_history(db_path, "2026-03-27")
    assert len(result) == 2  # docs.python.org + mdn.io

    python = next(d for d in result if d["domain"] == "docs.python.org")
    assert python["visits"] == 2
    assert python["from"] == "11:00"
    assert python["to"] == "11:30"


# --- domain grouping ---


def test_domain_grouping(tmp_path):
    """Múltiples URLs del mismo dominio se agrupan."""
    db_path = str(tmp_path / "History")
    visits = [
        (f"https://github.com/page{i}", f"Page {i}", _chrome_ts(9 + i))
        for i in range(10)
    ]
    _create_chrome_db(db_path, visits)
    result = read_chromium_history(db_path, "2026-03-27")
    assert len(result) == 1
    assert result[0]["domain"] == "github.com"
    assert result[0]["visits"] == 10
    assert len(result[0]["titles"]) == 5  # max 5


def test_titles_max_5(tmp_path):
    """Los títulos se limitan a 5 por dominio."""
    db_path = str(tmp_path / "History")
    visits = [
        (f"https://example.com/p{i}", f"Title {i}", _chrome_ts(9, i))
        for i in range(20)
    ]
    _create_chrome_db(db_path, visits)
    result = read_chromium_history(db_path, "2026-03-27")
    assert result[0]["titles"] == ["Title 0", "Title 1", "Title 2", "Title 3", "Title 4"]


# --- get_history_for_date ---


def test_get_history_for_date_integration(tmp_path):
    """Flow completo con Chrome mock."""
    db_path = str(tmp_path / "History")
    _create_chrome_db(db_path, [
        ("https://github.com/pulls", "PRs", _chrome_ts(9, 0)),
        ("https://slack.com/messages", "Slack", _chrome_ts(10, 0)),
    ])
    with patch("mimir_daemon.browser_history.detect_browsers", return_value=[
        {"name": "chrome", "path": db_path},
    ]):
        result = get_history_for_date("2026-03-27")
    assert len(result) == 2
    domains = {d["domain"] for d in result}
    assert "github.com" in domains
    assert "slack.com" in domains


def test_get_history_no_browsers():
    """Retorna vacío si no hay navegadores."""
    with patch("mimir_daemon.browser_history.detect_browsers", return_value=[]):
        result = get_history_for_date("2026-03-27")
    assert result == []


def test_top_50_limit(tmp_path):
    """Se limita a 50 dominios."""
    db_path = str(tmp_path / "History")
    visits = [
        (f"https://domain{i}.com/page", f"D{i}", _chrome_ts(9, i % 60))
        for i in range(60)
    ]
    _create_chrome_db(db_path, visits)
    with patch("mimir_daemon.browser_history.detect_browsers", return_value=[
        {"name": "chrome", "path": db_path},
    ]):
        result = get_history_for_date("2026-03-27")
    assert len(result) == 50
