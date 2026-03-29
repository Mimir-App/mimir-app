"""Lectura y resolución de mapeos TOML para generación de bloques.

Lee ~/.config/mimir/mappings.toml y resuelve las reglas contra los datos
reales del día (señales, eventos VCS, calendario) para producir
context_mappings virtuales que se inyectan en generation-data.
"""

import logging
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)

_DEFAULT_PATH = Path.home() / ".config" / "mimir" / "mappings.toml"


def load_mappings(path: str | None = None) -> dict | None:
    """Lee y parsea el archivo TOML de mapeos.

    Retorna None si el archivo no existe o hay error de parseo.
    """
    toml_path = Path(path) if path else _DEFAULT_PATH
    if not toml_path.exists():
        return None

    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        logger.info("Mapeos TOML cargados: %s", toml_path)
        return data
    except Exception as e:
        logger.warning("Error leyendo mapeos TOML %s: %s", toml_path, e)
        return None


def resolve_context_rules(
    rules: list[dict],
    db_mappings: list[dict],
) -> list[dict]:
    """Convierte [[context_rules]] a formato compacto de context_mappings.

    TOML tiene prioridad sobre mapeos aprendidos en DB (admin > auto).
    """
    result = []
    for rule in rules:
        ctx = rule.get("ctx", "")
        if not ctx:
            continue
        result.append(_compact_mapping(
            ctx=ctx,
            pid=rule.get("project_id"),
            pname=rule.get("project_name", ""),
            tid=rule.get("task_id"),
            tname=rule.get("task_name", ""),
        ))
    return result


def resolve_branch_rules(
    rules: list[dict],
    signals: list[dict],
    branch_task_hints: dict,
) -> list[dict]:
    """Resuelve [[branch_rules]] contra las señales del día.

    Para cada regla, busca señales cuya rama contenga el pattern.
    Genera context_mappings virtuales usando el ctx de esas señales.
    """
    result = []
    seen_ctx: set[str] = set()

    for rule in rules:
        pattern = rule.get("pattern", "").lower()
        if not pattern:
            continue

        for signal in signals:
            branch = (signal.get("branch") or "").lower()
            ctx = signal.get("ctx", "")
            if not branch or not ctx or pattern not in branch:
                continue
            if ctx in seen_ctx:
                continue
            seen_ctx.add(ctx)
            result.append(_compact_mapping(
                ctx=ctx,
                pid=rule.get("project_id"),
                pname=rule.get("project_name", ""),
                tid=rule.get("task_id"),
                tname=rule.get("task_name", ""),
            ))

    return result


def resolve_calendar_rules(
    rules: list[dict],
    calendar_events: list[dict],
    target_month: str,
    target_year: str,
) -> list[dict]:
    """Resuelve [[calendar_rules]] contra los eventos del día.

    Enriquece los eventos de calendario con pid/pname/task_pattern/type.
    Expande {month} y {year} en task_pattern.
    Retorna una copia de calendar_events con campos extra.
    """
    enriched = []
    for event in calendar_events:
        event_copy = dict(event)
        event_name = (event.get("name") or "").lower()

        for rule in rules:
            pattern = (rule.get("pattern") or "").lower()
            if not pattern or pattern not in event_name:
                continue

            # Match encontrado — enriquecer evento
            event_copy["pid"] = rule.get("project_id")
            event_copy["pname"] = rule.get("project_name", "")
            if rule.get("task_pattern"):
                event_copy["task_pattern"] = (
                    rule["task_pattern"]
                    .replace("{month}", target_month)
                    .replace("{year}", target_year)
                )
            if rule.get("type"):
                event_copy["type"] = rule["type"]
            break  # primera regla que haga match gana

        enriched.append(event_copy)
    return enriched


def resolve_app_rules(
    rules: list[dict],
    signals: list[dict],
) -> list[dict]:
    """Resuelve [[app_rules]] contra las señales del día.

    Solo aplica si la señal NO tiene un context_key tipo git: (para no
    sobreescribir mapeos más específicos de repositorios).
    """
    result = []
    seen_ctx: set[str] = set()

    for rule in rules:
        app_pattern = (rule.get("app") or "").lower()
        if not app_pattern:
            continue

        for signal in signals:
            app = (signal.get("app") or "").lower()
            ctx = signal.get("ctx", "")
            # Solo aplicar si coincide la app y no hay ctx de git
            if app != app_pattern:
                continue
            if ctx.startswith("git:"):
                continue
            # Usar app como ctx virtual si no hay ctx
            virtual_ctx = ctx or f"app:{rule.get('app', '')}"
            if virtual_ctx in seen_ctx:
                continue
            seen_ctx.add(virtual_ctx)
            result.append(_compact_mapping(
                ctx=virtual_ctx,
                pid=rule.get("project_id"),
                pname=rule.get("project_name", ""),
                tid=rule.get("task_id"),
                tname=rule.get("task_name", ""),
            ))

    return result


def resolve_all(
    toml_data: dict,
    signals: list[dict],
    calendar_events: list[dict],
    db_mappings: list[dict],
    branch_task_hints: dict,
    target_month: str,
    target_year: str,
) -> dict:
    """Orquesta la resolución de todas las reglas TOML.

    Retorna un dict con:
    - extra_mappings: lista de context_mappings virtuales
    - enriched_calendar: calendar_events enriquecidos
    - defaults: dict con pid/pname/confidence por defecto
    - matched_project_ids: set de IDs de proyectos referenciados
    """
    extra_mappings: list[dict] = []
    matched_project_ids: set[int] = set()

    # 1. context_rules — máxima prioridad
    ctx_rules = toml_data.get("context_rules", [])
    if ctx_rules:
        ctx_mappings = resolve_context_rules(ctx_rules, db_mappings)
        extra_mappings.extend(ctx_mappings)

    # 2. branch_rules
    branch_rules = toml_data.get("branch_rules", [])
    if branch_rules:
        branch_mappings = resolve_branch_rules(
            branch_rules, signals, branch_task_hints,
        )
        # No duplicar con context_rules
        existing_ctx = {m["ctx"] for m in extra_mappings}
        for m in branch_mappings:
            if m["ctx"] not in existing_ctx:
                extra_mappings.append(m)
                existing_ctx.add(m["ctx"])

    # 3. app_rules — solo para signals sin git ctx
    app_rules = toml_data.get("app_rules", [])
    if app_rules:
        app_mappings = resolve_app_rules(app_rules, signals)
        existing_ctx = {m["ctx"] for m in extra_mappings}
        for m in app_mappings:
            if m["ctx"] not in existing_ctx:
                extra_mappings.append(m)
                existing_ctx.add(m["ctx"])

    # 4. calendar_rules
    cal_rules = toml_data.get("calendar_rules", [])
    enriched_calendar = calendar_events
    if cal_rules:
        enriched_calendar = resolve_calendar_rules(
            cal_rules, calendar_events, target_month, target_year,
        )

    # 5. Recopilar project IDs referenciados
    for m in extra_mappings:
        if m.get("pid"):
            matched_project_ids.add(m["pid"])
    for rule in cal_rules:
        if rule.get("project_id"):
            matched_project_ids.add(rule["project_id"])

    # 6. defaults
    defaults_section = toml_data.get("defaults", {})
    defaults = {}
    if defaults_section:
        defaults = _strip_none({
            "pid": defaults_section.get("project_id"),
            "pname": defaults_section.get("project_name", ""),
            "confidence": defaults_section.get("confidence"),
        })

    return {
        "extra_mappings": extra_mappings,
        "enriched_calendar": enriched_calendar,
        "defaults": defaults,
        "matched_project_ids": matched_project_ids,
    }


def _compact_mapping(
    ctx: str,
    pid: int | None = None,
    pname: str = "",
    tid: int | None = None,
    tname: str = "",
) -> dict:
    """Crea un mapping compacto eliminando campos vacíos."""
    m: dict = {"ctx": ctx}
    if pid is not None:
        m["pid"] = pid
    if pname:
        m["pname"] = pname
    if tid is not None:
        m["tid"] = tid
    if tname:
        m["tname"] = tname
    return m


def _strip_none(d: dict) -> dict:
    """Elimina campos con valor None de un dict."""
    return {k: v for k, v in d.items() if v is not None}
