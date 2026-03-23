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
    context_key TEXT,
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

CREATE TABLE IF NOT EXISTS item_preferences (
    item_id INTEGER NOT NULL,
    item_type TEXT NOT NULL CHECK(item_type IN ('issue', 'mr')),
    manual_score INTEGER DEFAULT 0,
    followed BOOLEAN DEFAULT FALSE,
    source TEXT,
    project_path TEXT,
    iid INTEGER,
    title TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (item_id, item_type)
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    link TEXT,
    item_id INTEGER,
    read BOOLEAN DEFAULT FALSE,
    created_at TEXT DEFAULT (datetime('now'))
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
    async with db.execute("PRAGMA table_info(blocks)") as cur:
        cols = [row[1] for row in await cur.fetchall()]
    if "window_titles_json" not in cols:
        await db.execute("ALTER TABLE blocks ADD COLUMN window_titles_json TEXT")


async def _m002_blocks_context_key(db: aiosqlite.Connection) -> None:
    """Anade columna context_key a blocks para auto-asignacion (v0.4.1)."""
    async with db.execute("PRAGMA table_info(blocks)") as cur:
        cols = [row[1] for row in await cur.fetchall()]
    if "context_key" not in cols:
        await db.execute("ALTER TABLE blocks ADD COLUMN context_key TEXT")
    # Backfill: inferir context_key desde la primera senal de cada bloque
    await db.execute("""
        UPDATE blocks SET context_key = (
            SELECT s.context_key FROM signals s
            JOIN block_signals bs ON s.id = bs.signal_id
            WHERE bs.block_id = blocks.id
            ORDER BY s.timestamp LIMIT 1
        ) WHERE context_key IS NULL
    """)


async def _m003_item_preferences_extra_cols(db: aiosqlite.Connection) -> None:
    """Anade columnas source, project_path, iid, title a item_preferences."""
    async with db.execute("PRAGMA table_info(item_preferences)") as cur:
        cols = [row[1] for row in await cur.fetchall()]
    for col, definition in [("source", "TEXT"), ("project_path", "TEXT"), ("iid", "INTEGER"), ("title", "TEXT")]:
        if col not in cols:
            await db.execute(f"ALTER TABLE item_preferences ADD COLUMN {col} {definition}")


async def _m004_context_affinity(db: aiosqlite.Connection) -> None:
    """Anade tabla context_affinity para aprendizaje de fusion de contextos (v0.5.0)."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS context_affinity (
            context_key_a TEXT NOT NULL,
            context_key_b TEXT NOT NULL,
            merge_count INTEGER NOT NULL DEFAULT 1,
            last_merged TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (context_key_a, context_key_b)
        )
    """)


MIGRATIONS: list[tuple[int, str, MigrationFn]] = [
    (1, "blocks.window_titles_json", _m001_blocks_window_titles_json),
    (2, "blocks.context_key + backfill", _m002_blocks_context_key),
    (3, "item_preferences extra cols", _m003_item_preferences_extra_cols),
    (4, "context_affinity table", _m004_context_affinity),
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

    async def delete_context_mapping(self, context_key: str) -> None:
        """Elimina un mapeo context_key -> Odoo."""
        await self.db.execute(
            "DELETE FROM context_mappings WHERE context_key = ?", (context_key,)
        )
        await self.db.commit()

    async def suggest_mapping(self, context_key: str) -> dict | None:
        """Busca sugerencia de mapeo para un context_key.

        Estrategia de busqueda:
        1. Coincidencia exacta
        2. Coincidencia parcial (mismo prefijo git:/web:/app: + substring)
        3. Ultimo bloque confirmado/synced con el mismo context_key
        """
        # 1. Exacta
        mapping = await self.get_context_mapping(context_key)
        if mapping:
            return {**mapping, "match": "exact"}

        # 2. Parcial: mismo tipo de contexto + substring comun
        prefix = context_key.split(":")[0] + ":" if ":" in context_key else ""
        if prefix:
            async with self.db.execute(
                "SELECT * FROM context_mappings WHERE context_key LIKE ? ORDER BY updated_at DESC LIMIT 1",
                (f"{prefix}%",),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {**dict(row), "match": "partial"}

        # 3. Historial: ultimo bloque con este context_key que tenga proyecto
        async with self.db.execute(
            """SELECT odoo_project_id, odoo_project_name, odoo_task_id, odoo_task_name
               FROM blocks
               WHERE context_key = ? AND odoo_project_id IS NOT NULL
               AND status IN ('confirmed', 'synced')
               ORDER BY start_time DESC LIMIT 1""",
            (context_key,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "context_key": context_key,
                    "odoo_project_id": row[0],
                    "odoo_project_name": row[1],
                    "odoo_task_id": row[2],
                    "odoo_task_name": row[3],
                    "match": "history",
                }

        return None

    # --- Context affinity (aprendizaje de fusion) ---

    async def record_context_affinity(self, context_keys: list[str]) -> None:
        """Registra afinidad entre pares de context_keys tras una fusion manual.

        Recibe la lista de context_keys de los bloques fusionados y crea/incrementa
        el merge_count para cada par unico.
        """
        unique_keys = list(dict.fromkeys(k for k in context_keys if k))
        if len(unique_keys) < 2:
            return
        for i, key_a in enumerate(unique_keys):
            for key_b in unique_keys[i + 1:]:
                # Ordenar alfabeticamente para clave consistente
                a, b = sorted([key_a, key_b])
                await self.db.execute(
                    """INSERT INTO context_affinity (context_key_a, context_key_b, merge_count, last_merged)
                       VALUES (?, ?, 1, datetime('now'))
                       ON CONFLICT(context_key_a, context_key_b)
                       DO UPDATE SET merge_count = merge_count + 1, last_merged = datetime('now')""",
                    (a, b),
                )
        await self.db.commit()

    async def get_context_affinity(self, key_a: str, key_b: str) -> dict | None:
        """Obtiene la afinidad entre dos context_keys."""
        a, b = sorted([key_a, key_b])
        async with self.db.execute(
            "SELECT * FROM context_affinity WHERE context_key_a = ? AND context_key_b = ?",
            (a, b),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_affine_keys(self, context_key: str, min_count: int = 3) -> set[str]:
        """Obtiene todos los context_keys con afinidad suficiente respecto a uno dado."""
        results: set[str] = set()
        async with self.db.execute(
            """SELECT context_key_a, context_key_b FROM context_affinity
               WHERE (context_key_a = ? OR context_key_b = ?) AND merge_count >= ?""",
            (context_key, context_key, min_count),
        ) as cursor:
            for row in await cursor.fetchall():
                other = row[1] if row[0] == context_key else row[0]
                results.add(other)
        return results

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

    # --- Item preferences ---

    async def upsert_item_preference(
        self, item_id: int, item_type: str,
        manual_score: int | None = None, followed: bool | None = None,
        source: str | None = None, project_path: str | None = None,
        iid: int | None = None, title: str | None = None,
    ) -> None:
        """Crea o actualiza preferencia de un item (issue o mr)."""
        async with self.db.execute(
            "SELECT * FROM item_preferences WHERE item_id = ? AND item_type = ?",
            (item_id, item_type),
        ) as cursor:
            existing = await cursor.fetchone()
        if existing:
            updates = []
            params: list = []
            if manual_score is not None:
                updates.append("manual_score = ?")
                params.append(manual_score)
            if followed is not None:
                updates.append("followed = ?")
                params.append(followed)
            if source is not None:
                updates.append("source = ?")
                params.append(source)
            if project_path is not None:
                updates.append("project_path = ?")
                params.append(project_path)
            if iid is not None:
                updates.append("iid = ?")
                params.append(iid)
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if updates:
                updates.append("updated_at = datetime('now')")
                params.extend([item_id, item_type])
                await self.db.execute(
                    f"UPDATE item_preferences SET {', '.join(updates)} "
                    "WHERE item_id = ? AND item_type = ?",
                    params,
                )
        else:
            await self.db.execute(
                "INSERT INTO item_preferences (item_id, item_type, manual_score, followed, source, project_path, iid, title) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, item_type, manual_score or 0, followed or False, source, project_path, iid, title),
            )
        await self.db.commit()

    async def get_followed_items_with_meta(self, item_type: str) -> list[dict]:
        """Obtiene items seguidos con metadatos (source, project_path, iid, title)."""
        async with self.db.execute(
            "SELECT * FROM item_preferences WHERE item_type = ? AND followed = 1",
            (item_type,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_item_preferences(self, item_type: str) -> list[dict]:
        """Obtiene todas las preferencias de un tipo de item."""
        async with self.db.execute(
            "SELECT * FROM item_preferences WHERE item_type = ?", (item_type,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_followed_item_ids(self, item_type: str) -> list[int]:
        """Obtiene IDs de items seguidos por tipo."""
        async with self.db.execute(
            "SELECT item_id FROM item_preferences WHERE item_type = ? AND followed = 1",
            (item_type,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [r["item_id"] for r in rows]

    # --- Notifications ---

    async def create_notification(
        self, type: str, title: str, body: str | None = None,
        link: str | None = None, item_id: int | None = None,
    ) -> int:
        """Crea una notificacion y retorna su ID."""
        async with self.db.execute(
            "INSERT INTO notifications (type, title, body, link, item_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (type, title, body, link, item_id),
        ) as cursor:
            await self.db.commit()
            return cursor.lastrowid  # type: ignore

    async def get_notifications(self, unread_only: bool = True) -> list[dict]:
        """Obtiene notificaciones, opcionalmente solo las no leidas."""
        query = "SELECT * FROM notifications"
        if unread_only:
            query += " WHERE read = 0"
        query += " ORDER BY created_at DESC"
        async with self.db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_notification_count(self) -> int:
        """Obtiene el numero de notificaciones no leidas."""
        async with self.db.execute(
            "SELECT COUNT(*) FROM notifications WHERE read = 0"
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def mark_notification_read(self, notification_id: int) -> None:
        """Marca una notificacion como leida."""
        await self.db.execute(
            "UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,)
        )
        await self.db.commit()

    async def mark_all_notifications_read(self) -> None:
        """Marca todas las notificaciones como leidas."""
        await self.db.execute("UPDATE notifications SET read = 1 WHERE read = 0")
        await self.db.commit()

    async def cleanup_old_notifications(self, days: int = 7) -> int:
        """Elimina notificaciones mas antiguas de N dias."""
        async with self.db.execute(
            "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
            (f"-{days} days",),
        ) as cursor:
            await self.db.commit()
            return cursor.rowcount
