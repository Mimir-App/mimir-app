"""Base de datos SQLite para el daemon."""

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA = """
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
"""


class Database:
    """Gestor de base de datos async."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Conecta y crea el esquema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.commit()
        logger.info("Base de datos conectada: %s", self.db_path)

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
