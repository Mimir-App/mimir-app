"""Lectura de historial de navegadores para enriquecer la generación de bloques.

Lee las bases de datos SQLite locales de Chrome, Firefox y derivados.
Los navegadores bloquean sus DBs, así que se copian a un archivo temporal
antes de leer. Solo se lee bajo demanda al generar bloques.
"""

import base64
import glob
import logging
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Rutas conocidas de iconos del sistema (Linux)
_ICON_SEARCH_PATHS = [
    "/usr/share/icons/hicolor/48x48/apps",
    "/usr/share/icons/hicolor/32x32/apps",
    "/usr/share/icons/hicolor/24x24/apps",
    "/usr/share/pixmaps",
]

# Nombre del icono por navegador
_ICON_NAMES: dict[str, list[str]] = {
    "chrome": ["google-chrome.png"],
    "chromium": ["chromium.png", "chromium-browser.png"],
    "brave": ["brave-browser.png", "brave.png"],
    "vivaldi": ["vivaldi.png"],
    "edge": ["microsoft-edge.png"],
    "opera": ["opera.png"],
    "firefox": ["firefox.png"],
}

# Rutas conocidas de historial en Linux
BROWSER_PROFILES: dict[str, str] = {
    "chrome": "~/.config/google-chrome/Default/History",
    "chromium": "~/.config/chromium/Default/History",
    "brave": "~/.config/BraveSoftware/Brave-Browser/Default/History",
    "vivaldi": "~/.config/vivaldi/Default/History",
    "edge": "~/.config/microsoft-edge/Default/History",
    "opera": "~/.config/opera/Default/History",
    # Firefox usa glob por el nombre de perfil variable
    "firefox": "~/.mozilla/firefox/*.default-release/places.sqlite",
}

# Epoch de Chrome/Chromium: microsegundos desde 1601-01-01
_CHROME_EPOCH_OFFSET = 11644473600  # segundos entre 1601 y 1970


def detect_browsers() -> list[dict]:
    """Detecta navegadores instalados comprobando si existe su DB de historial.

    Retorna lista con name, path e icon (data URI base64 del icono del sistema).
    """
    found = []
    for name, pattern in BROWSER_PROFILES.items():
        expanded = str(Path(pattern).expanduser())
        if name == "firefox":
            matches = glob.glob(expanded)
            if not matches:
                fallback = expanded.replace("*.default-release", "*.default")
                matches = glob.glob(fallback)
            if matches:
                found.append({"name": name, "path": matches[0], "icon": _find_icon(name)})
        else:
            path = Path(expanded)
            if path.exists():
                found.append({"name": name, "path": str(path), "icon": _find_icon(name)})
    return found


def _find_icon(browser_name: str) -> str | None:
    """Busca el icono del navegador en las rutas del sistema y lo devuelve como data URI."""
    icon_names = _ICON_NAMES.get(browser_name, [])
    for search_dir in _ICON_SEARCH_PATHS:
        for icon_name in icon_names:
            icon_path = Path(search_dir) / icon_name
            if icon_path.exists():
                try:
                    data = icon_path.read_bytes()
                    b64 = base64.b64encode(data).decode("ascii")
                    ext = icon_path.suffix.lstrip(".")
                    mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
                    return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
    return None


def read_chromium_history(db_path: str, date: str) -> list[dict]:
    """Lee el historial de un navegador Chromium para una fecha.

    Copia la DB a un archivo temporal (el navegador la tiene bloqueada),
    consulta las visitas del día y agrupa por dominio.
    """
    tmp_path = None
    try:
        # Copiar DB a temporal
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp_path = tmp.name
        tmp.close()
        shutil.copy2(db_path, tmp_path)

        # Copiar WAL si existe (Chrome usa WAL mode)
        wal_path = db_path + "-wal"
        if Path(wal_path).exists():
            shutil.copy2(wal_path, tmp_path + "-wal")

        # Calcular rango de timestamps Chrome para el día
        target = datetime.strptime(date, "%Y-%m-%d")
        start_us = _datetime_to_chrome_us(target)
        end_us = _datetime_to_chrome_us(target + timedelta(days=1))

        conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT u.url, u.title, v.visit_time
                FROM visits v
                JOIN urls u ON v.url = u.id
                WHERE v.visit_time >= ? AND v.visit_time < ?
                ORDER BY v.visit_time
                """,
                (start_us, end_us),
            ).fetchall()
        finally:
            conn.close()

        return _group_by_domain(rows, chrome_epoch=True)

    except Exception as e:
        logger.warning("Error leyendo historial Chromium %s: %s", db_path, e)
        return []
    finally:
        _cleanup_temp(tmp_path)


def read_firefox_history(db_path: str, date: str) -> list[dict]:
    """Lee el historial de Firefox para una fecha.

    Firefox usa microsegundos desde Unix epoch (1970-01-01).
    """
    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp_path = tmp.name
        tmp.close()
        shutil.copy2(db_path, tmp_path)

        wal_path = db_path + "-wal"
        if Path(wal_path).exists():
            shutil.copy2(wal_path, tmp_path + "-wal")

        target = datetime.strptime(date, "%Y-%m-%d")
        start_us = int(target.timestamp()) * 1_000_000
        end_us = int((target + timedelta(days=1)).timestamp()) * 1_000_000

        conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT p.url, p.title, h.visit_date AS visit_time
                FROM moz_historyvisits h
                JOIN moz_places p ON h.place_id = p.id
                WHERE h.visit_date >= ? AND h.visit_date < ?
                ORDER BY h.visit_date
                """,
                (start_us, end_us),
            ).fetchall()
        finally:
            conn.close()

        return _group_by_domain(rows, chrome_epoch=False)

    except Exception as e:
        logger.warning("Error leyendo historial Firefox %s: %s", db_path, e)
        return []
    finally:
        _cleanup_temp(tmp_path)


def get_history_for_date(date: str, only_browsers: list[str] | None = None) -> list[dict]:
    """Lee el historial de los navegadores detectados para una fecha.

    Args:
        date: Fecha en formato YYYY-MM-DD.
        only_browsers: Lista de nombres de navegadores a usar (ej: ["chrome", "firefox"]).
                       Si es None o vacía, usa todos los detectados.

    Agrupa resultados por dominio (merge entre navegadores) y retorna
    los top 50 dominios por número de visitas.
    """
    browsers = detect_browsers()
    if only_browsers:
        browsers = [b for b in browsers if b["name"] in only_browsers]
    if not browsers:
        return []

    all_entries: list[dict] = []
    for browser in browsers:
        logger.info("Leyendo historial de %s: %s", browser["name"], browser["path"])
        if browser["name"] == "firefox":
            entries = read_firefox_history(browser["path"], date)
        else:
            entries = read_chromium_history(browser["path"], date)
        all_entries.extend(entries)

    if not all_entries:
        return []

    # Merge dominios duplicados (de diferentes navegadores)
    merged = _merge_domains(all_entries)

    # Ordenar por visitas desc, limitar a 50
    merged.sort(key=lambda d: d["visits"], reverse=True)
    return merged[:50]


# --- Helpers internos ---


def _datetime_to_chrome_us(dt: datetime) -> int:
    """Convierte datetime a microsegundos en epoch Chrome (desde 1601-01-01)."""
    unix_ts = int(dt.timestamp())
    return (unix_ts + _CHROME_EPOCH_OFFSET) * 1_000_000


def _chrome_us_to_time(us: int) -> str:
    """Convierte microsegundos Chrome a HH:MM local."""
    unix_ts = (us / 1_000_000) - _CHROME_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_ts).strftime("%H:%M")


def _unix_us_to_time(us: int) -> str:
    """Convierte microsegundos Unix a HH:MM local."""
    return datetime.fromtimestamp(us / 1_000_000).strftime("%H:%M")


def _extract_domain(url: str) -> str | None:
    """Extrae el dominio de una URL, ignorando URLs internas del navegador."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None
        host = parsed.hostname or ""
        # Quitar www.
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


def _group_by_domain(rows: list, chrome_epoch: bool = True) -> list[dict]:
    """Agrupa visitas por dominio con conteo, rango de tiempo y títulos."""
    domains: dict[str, dict] = {}
    time_fn = _chrome_us_to_time if chrome_epoch else _unix_us_to_time

    for row in rows:
        url = row["url"] if isinstance(row, sqlite3.Row) else row[0]
        title = row["title"] if isinstance(row, sqlite3.Row) else row[1]
        visit_time = row["visit_time"] if isinstance(row, sqlite3.Row) else row[2]

        domain = _extract_domain(url)
        if not domain:
            continue

        t = time_fn(visit_time)

        if domain not in domains:
            domains[domain] = {
                "domain": domain,
                "visits": 0,
                "from": t,
                "to": t,
                "_titles_set": set(),
                "titles": [],
            }

        d = domains[domain]
        d["visits"] += 1
        if t < d["from"]:
            d["from"] = t
        if t > d["to"]:
            d["to"] = t
        if title and title not in d["_titles_set"] and len(d["titles"]) < 5:
            d["_titles_set"].add(title)
            d["titles"].append(title[:80])

    # Limpiar sets internos
    result = []
    for d in domains.values():
        del d["_titles_set"]
        result.append(d)

    return result


def _merge_domains(entries: list[dict]) -> list[dict]:
    """Merge entradas con el mismo dominio (de diferentes navegadores)."""
    merged: dict[str, dict] = {}
    for entry in entries:
        domain = entry["domain"]
        if domain not in merged:
            merged[domain] = {
                "domain": domain,
                "visits": entry["visits"],
                "from": entry["from"],
                "to": entry["to"],
                "titles": list(entry["titles"]),
            }
        else:
            m = merged[domain]
            m["visits"] += entry["visits"]
            if entry["from"] < m["from"]:
                m["from"] = entry["from"]
            if entry["to"] > m["to"]:
                m["to"] = entry["to"]
            for t in entry["titles"]:
                if t not in m["titles"] and len(m["titles"]) < 5:
                    m["titles"].append(t)
    return list(merged.values())


def _cleanup_temp(tmp_path: str | None) -> None:
    """Elimina archivos temporales de forma segura."""
    if not tmp_path:
        return
    try:
        Path(tmp_path).unlink(missing_ok=True)
        Path(tmp_path + "-wal").unlink(missing_ok=True)
        Path(tmp_path + "-shm").unlink(missing_ok=True)
    except Exception:
        pass
