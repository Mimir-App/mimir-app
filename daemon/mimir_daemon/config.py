"""Configuración del daemon."""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "mimir"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "daemon.db"


@dataclass
class DaemonConfig:
    """Configuración del daemon de captura."""

    port: int = 9477
    host: str = "127.0.0.1"
    polling_interval: int = 30  # segundos
    inherit_threshold: int = 900  # legacy, no usado en signal_aggregator
    inactivity_threshold: int = 300  # 5 minutos en segundos
    checkpoint_interval: int = 5  # cada N polls
    db_path: str = str(DEFAULT_DB_PATH)
    log_level: str = "INFO"
    browser_apps: list[str] | None = None
    transient_apps: list[str] | None = None
    # Permisos de captura
    capture_window: bool = True
    capture_git: bool = True
    capture_idle: bool = True
    capture_audio: bool = True
    capture_ssh: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> "DaemonConfig":
        """Carga la configuración desde archivo JSON."""
        config_file = path or (DEFAULT_CONFIG_DIR / "daemon.json")
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception as e:
                logger.warning("Error cargando config, usando defaults: %s", e)
        return cls()

    def save(self, path: Path | None = None) -> None:
        """Guarda la configuración a archivo JSON."""
        config_file = path or (DEFAULT_CONFIG_DIR / "daemon.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
