"""Base de datos SQLite para el daemon."""

import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Tipo para funciones de migracion
MigrationFn = Callable[[aiosqlite.Connection], Coroutine[Any, Any, None]]

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    duration_minutes REAL NOT NULL DEFAULT 0,
    app_name TEXT NOT NULL DEFAULT '',
    window_title TEXT NOT NULL DEFAULT '',
    project_path TEXT,
    git_branch TEXT,
    git_remote TEXT,
    ai_description TEXT,
    ai_confidence REAL,
    user_description TEXT,
    odoo_project_id INTEGER,
    odoo_task_id INTEGER,
    odoo_project_name TEXT,
    odoo_task_name TEXT,
    status TEXT NOT NULL DEFAULT 'auto',
    sync_error TEXT,
    odoo_entry_id INTEGER,
    window_titles_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_blocks_date
    ON blocks(date(start_time));

CREATE INDEX IF NOT EXISTS idx_blocks_status
    ON blocks(status);

CREATE TABLE IF NOT EXISTS source_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_id INTEGER NOT NULL REFERENCES blocks(id),
    token_type TEXT NOT NULL,
    token_value TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS preferences_cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_cache (
    signal_hash TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    confidence REAL NOT NULL,
    provider TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS context_mappings (
    context_key TEXT PRIMARY KEY,
    odoo_project_id INTEGER,
    odoo_project_name TEXT,
    odoo_task_id INTEGER,
    odoo_task_name TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    app_name TEXT,
    window_title TEXT,
    project_path TEXT,
    git_branch TEXT,
    git_remote TEXT,
    ssh_host TEXT,
    pid INTEGER,
    context_key TEXT,
    last_commit_message TEXT,
    idle_ms INTEGER DEFAULT 0,
    audio_app TEXT,
    is_meeting INTEGER DEFAULT 0,
    workspace TEXT,
    calendar_event TEXT,
    calendar_attendees TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);

CREATE TABLE IF NOT EXISTS block_signals (
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    signal_id INTEGER NOT NULL REFERENCES signals(id),
    PRIMARY KEY (block_id, signal_id)
);
"""


# --- Migraciones versionadas ---
# Cada tupla: (version, descripcion, funcion async)
# Las funciones reciben la conexion aiosqlite.
# NUNCA eliminar ni reordenar migraciones existentes, solo anadir al final.

async def _m001_blocks_window_titles_json(db: aiosqlite.Connection) -> None:
    """Anade columna window_titles_json a blocks (v0.3.0)."""
    # Verificar si ya existe (DB creada con schema nuevo)
    async with db.execute("PRAGMA table_info(blocks)") as cur:
        cols = [row[1] for row in await cur.fetchall()]
    if "window_titles_json" not in cols:
        await db.execute("ALTER TABLE blocks ADD COLUMN window_titles_json TEXT")


MIGRATIONS: list[tuple[int, str, MigrationFn]] = [
    (1, "blocks.window_titles_json", _m001_blocks_window_titles_json),
]


class Database:
    """Gestor de base de datos async."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Conecta, crea el esquema y aplica migraciones."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._run_migrations()
        await self._db.commit()
        logger.info("Base de datos conectada: %s", self.db_path)

    async def _get_schema_version(self) -> int:
        """Obtiene la version actual del esquema."""
        try:
            async with self._db.execute(  # type: ignore
                "SELECT MAX(version) FROM schema_version"
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] is not None else 0
        except Exception:
            return 0

    async def _set_schema_version(self, version: int) -> None:
        """Registra una version de migracion como aplicada."""
        await self._db.execute(  # type: ignore
            "INSERT INTO schema_version (version) VALUES (?)", (version,)
        )

    async def _run_migrations(self) -> None:
        """Aplica migraciones pendientes en orden secuencial."""
        current = await self._get_schema_version()
        pending = [(v, desc, fn) for v, desc, fn in MIGRATIONS if v > current]
        if not pending:
            return
        for version, description, migrate_fn in pending:
            await migrate_fn(self._db)  # type: ignore
            await self._set_schema_version(version)
            logger.info("Migración v%d aplicada: %s", version, description)

    async def close(self) -> None:
        """Cierra la conexion."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Retorna la conexion activa."""
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db

    # --- Blocks: queries ---

    async def get_blocks_by_date(self, date: str) -> list[dict]:
        """Obtiene bloques de un dia."""
        async with self.db.execute(
            "SELECT * FROM blocks WHERE date(start_time) = ? ORDER BY start_time",
            (date,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_block_by_id(self, block_id: int) -> dict | None:
        """Obtiene un bloque por su ID."""
        async with self.db.execute(
            "SELECT * FROM blocks WHERE id = ?",
            (block_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_open_blocks(self) -> list[dict]:
        """Obtiene bloques con status 'auto' (no cerrados)."""
        async with self.db.execute(
            "SELECT * FROM blocks WHERE status = 'auto' ORDER BY start_time DESC",
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def count_blocks_today(self) -> int:
        """Cuenta bloques del dia actual."""
        async with self.db.execute(
            "SELECT COUNT(*) FROM blocks WHERE date(start_time) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_blocks_summary(self, date: str) -> dict:
        """Obtiene un resumen estadistico de los bloques de un dia."""
        blocks = await self.get_blocks_by_date(date)
        total_minutes = sum(b.get("duration_minutes", 0) for b in blocks)
        statuses = {}
        for b in blocks:
            s = b.get("status", "auto")
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "date": date,
            "total_blocks": len(blocks),
            "total_minutes": round(total_minutes, 1),
            "total_hours": round(total_minutes / 60, 2) if total_minutes else 0,
            "by_status": statuses,
        }

    # --- Blocks: mutations ---

    async def create_block(self, **kwargs: object) -> int:
        """Crea un nuevo bloque y retorna su ID."""
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        async with self.db.execute(
            f"INSERT INTO blocks ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        ) as cursor:
            await self.db.commit()
            return cursor.lastrowid  # type: ignore

    async def update_block(self, block_id: int, **kwargs: object) -> None:
        """Actualiza campos de un bloque."""
        if not kwargs:
            return
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [block_id]
        await self.db.execute(
            f"UPDATE blocks SET {sets} WHERE id = ?",
            values,
        )
        await self.db.commit()

    async def delete_block(self, block_id: int) -> None:
        """Elimina un bloque."""
        await self.db.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
        await self.db.commit()

    # --- Preferences cache ---

    async def get_preference(self, key: str) -> str | None:
        """Obtiene un valor de la cache de preferencias."""
        async with self.db.execute(
            "SELECT value FROM preferences_cache WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_preference(self, key: str, value: str) -> None:
        """Guarda un valor en la cache de preferencias."""
        await self.db.execute(
            "INSERT OR REPLACE INTO preferences_cache (key, value, updated_at) "
            "VALUES (?, ?, datetime('now'))",
            (key, value),
        )
        await self.db.commit()

    # --- AI cache ---

    async def get_ai_cache(self, signal_hash: str) -> dict | None:
        """Obtiene una descripción cacheada por hash de señales."""
        async with self.db.execute(
            "SELECT * FROM ai_cache WHERE signal_hash = ?", (signal_hash,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_ai_cache(
        self, signal_hash: str, description: str, confidence: float, provider: str
    ) -> None:
        """Guarda una descripción en la cache."""
        await self.db.execute(
            "INSERT OR REPLACE INTO ai_cache (signal_hash, description, confidence, provider) "
            "VALUES (?, ?, ?, ?)",
            (signal_hash, description, confidence, provider),
        )
        await self.db.commit()

    # --- Context mappings ---

    async def get_context_mapping(self, context_key: str) -> dict | None:
        """Obtiene el mapeo Odoo para un context_key."""
        async with self.db.execute(
            "SELECT * FROM context_mappings WHERE context_key = ?",
            (context_key,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def set_context_mapping(
        self, context_key: str, odoo_project_id: int | None,
        odoo_project_name: str | None, odoo_task_id: int | None,
        odoo_task_name: str | None,
    ) -> None:
        """Guarda o actualiza el mapeo Odoo para un context_key."""
        await self.db.execute(
            """INSERT OR REPLACE INTO context_mappings
               (context_key, odoo_project_id, odoo_project_name, odoo_task_id, odoo_task_name, updated_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (context_key, odoo_project_id, odoo_project_name, odoo_task_id, odoo_task_name),
        )
        await self.db.commit()

    async def get_all_context_mappings(self) -> list[dict]:
        """Obtiene todos los mapeos context_key -> Odoo."""
        async with self.db.execute(
            "SELECT * FROM context_mappings ORDER BY updated_at DESC",
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # --- Signals ---

    async def create_signal(self, **kwargs: object) -> int:
        """Inserta una senal y devuelve su ID."""
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        async with self.db.execute(
            f"INSERT INTO signals ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        ) as cursor:
            await self.db.commit()
            return cursor.lastrowid  # type: ignore

    async def get_signals_by_date(self, date: str) -> list[dict]:
        """Obtiene senales de un dia."""
        async with self.db.execute(
            "SELECT * FROM signals WHERE date(timestamp) = ? ORDER BY timestamp",
            (date,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_signals_by_block(self, block_id: int) -> list[dict]:
        """Obtiene senales asociadas a un bloque."""
        async with self.db.execute(
            """SELECT s.* FROM signals s
               JOIN block_signals bs ON s.id = bs.signal_id
               WHERE bs.block_id = ?
               ORDER BY s.timestamp""",
            (block_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def link_signal_to_block(self, block_id: int, signal_id: int) -> None:
        """Vincula una senal a un bloque."""
        await self.db.execute(
            "INSERT OR IGNORE INTO block_signals (block_id, signal_id) VALUES (?, ?)",
            (block_id, signal_id),
        )
        await self.db.commit()

    async def cleanup_old_signals(self, months: int = 6) -> int:
        """Elimina senales mas antiguas de N meses."""
        async with self.db.execute(
            "DELETE FROM signals WHERE timestamp < datetime('now', ?)",
            (f"-{months} months",),
        ) as cursor:
            await self.db.commit()
            return cursor.rowcount
