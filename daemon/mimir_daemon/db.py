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
        """Cierra la conexión."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Retorna la conexión activa."""
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db

    async def get_blocks_by_date(self, date: str) -> list[dict]:
        """Obtiene bloques de un día."""
        async with self.db.execute(
            "SELECT * FROM blocks WHERE date(start_time) = ? ORDER BY start_time",
            (date,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def create_block(self, **kwargs) -> int:
        """Crea un nuevo bloque y retorna su ID."""
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        async with self.db.execute(
            f"INSERT INTO blocks ({cols}) VALUES ({placeholders})",
            tuple(kwargs.values()),
        ) as cursor:
            await self.db.commit()
            return cursor.lastrowid  # type: ignore

    async def update_block(self, block_id: int, **kwargs) -> None:
        """Actualiza campos de un bloque."""
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [block_id]
        await self.db.execute(
            f"UPDATE blocks SET {sets} WHERE id = ?",
            values,
        )
        await self.db.commit()

    async def count_blocks_today(self) -> int:
        """Cuenta bloques del día actual."""
        async with self.db.execute(
            "SELECT COUNT(*) FROM blocks WHERE date(start_time) = date('now')"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
