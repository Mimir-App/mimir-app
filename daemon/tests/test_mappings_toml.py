"""Tests para el módulo de mapeos TOML."""

import pytest

from mimir_daemon.mappings_toml import (
    load_mappings,
    resolve_all,
    resolve_app_rules,
    resolve_branch_rules,
    resolve_calendar_rules,
    resolve_context_rules,
)


# --- load_mappings ---


def test_load_mappings_not_found(tmp_path):
    """Retorna None si el archivo no existe."""
    result = load_mappings(str(tmp_path / "no-existe.toml"))
    assert result is None


def test_load_mappings_invalid(tmp_path):
    """Retorna None si el TOML es inválido."""
    bad_file = tmp_path / "bad.toml"
    bad_file.write_text("esto no es [ toml válido !!!")
    result = load_mappings(str(bad_file))
    assert result is None


def test_load_mappings_valid(tmp_path):
    """Parsea correctamente un TOML válido."""
    toml_file = tmp_path / "mappings.toml"
    toml_file.write_text(
        '[meta]\nversion = 1\n\n'
        '[[context_rules]]\nctx = "git:org/repo"\nproject_id = 5\n'
        'project_name = "Proyecto"\n'
    )
    result = load_mappings(str(toml_file))
    assert result is not None
    assert result["meta"]["version"] == 1
    assert len(result["context_rules"]) == 1
    assert result["context_rules"][0]["ctx"] == "git:org/repo"


# --- resolve_context_rules ---


def test_resolve_context_rules_match():
    """Genera mapping compacto para context_rules."""
    rules = [
        {"ctx": "git:org/repo", "project_id": 5, "project_name": "Proj", "task_id": 100, "task_name": "Task 100"},
    ]
    result = resolve_context_rules(rules, db_mappings=[])
    assert len(result) == 1
    assert result[0] == {"ctx": "git:org/repo", "pid": 5, "pname": "Proj", "tid": 100, "tname": "Task 100"}


def test_resolve_context_rules_overrides_db():
    """TOML genera mapping incluso si ya existe en DB (TOML tiene prioridad)."""
    rules = [{"ctx": "git:org/repo", "project_id": 10, "project_name": "TOML Proj"}]
    db_mappings = [{"context_key": "git:org/repo", "odoo_project_id": 5, "odoo_project_name": "DB Proj"}]
    result = resolve_context_rules(rules, db_mappings)
    assert len(result) == 1
    assert result[0]["pid"] == 10
    assert result[0]["pname"] == "TOML Proj"


def test_resolve_context_rules_skips_empty_ctx():
    """Ignora reglas sin ctx."""
    rules = [{"project_id": 5}]
    result = resolve_context_rules(rules, db_mappings=[])
    assert len(result) == 0


def test_resolve_context_rules_omits_empty_fields():
    """Campos vacíos no aparecen en el mapping compacto."""
    rules = [{"ctx": "git:org/repo", "project_id": 5}]
    result = resolve_context_rules(rules, db_mappings=[])
    assert len(result) == 1
    assert "tid" not in result[0]
    assert "tname" not in result[0]
    assert "pname" not in result[0]


# --- resolve_branch_rules ---


def test_resolve_branch_rules_match():
    """Genera mapping virtual cuando la rama contiene el pattern."""
    rules = [{"pattern": "gextia", "project_id": 5, "project_name": "Gextia"}]
    signals = [
        {"branch": "feat/gextia_8119", "ctx": "git:org/gextia", "app": "Code"},
        {"branch": "feat/gextia_8119", "ctx": "git:org/gextia", "app": "Terminal"},  # mismo ctx, no duplicar
    ]
    result = resolve_branch_rules(rules, signals, branch_task_hints={})
    assert len(result) == 1
    assert result[0]["ctx"] == "git:org/gextia"
    assert result[0]["pid"] == 5


def test_resolve_branch_rules_no_match():
    """No genera mapping si la rama no contiene el pattern."""
    rules = [{"pattern": "gextia", "project_id": 5, "project_name": "Gextia"}]
    signals = [{"branch": "feat/other_123", "ctx": "git:org/other", "app": "Code"}]
    result = resolve_branch_rules(rules, signals, branch_task_hints={})
    assert len(result) == 0


def test_resolve_branch_rules_case_insensitive():
    """El match de patrón es case-insensitive."""
    rules = [{"pattern": "gextia", "project_id": 5, "project_name": "Gextia"}]
    signals = [{"branch": "feat/GEXTIA_8119", "ctx": "git:org/gextia", "app": "Code"}]
    result = resolve_branch_rules(rules, signals, branch_task_hints={})
    assert len(result) == 1


def test_resolve_branch_rules_no_ctx():
    """No genera mapping si la señal no tiene ctx."""
    rules = [{"pattern": "gextia", "project_id": 5}]
    signals = [{"branch": "feat/gextia_8119", "ctx": "", "app": "Code"}]
    result = resolve_branch_rules(rules, signals, branch_task_hints={})
    assert len(result) == 0


# --- resolve_calendar_rules ---


def test_resolve_calendar_rules_match():
    """Enriquece evento cuando el nombre coincide con el pattern."""
    rules = [
        {
            "pattern": "Daily",
            "project_id": 12,
            "project_name": "Temas internos",
            "task_pattern": "Daily - {month} {year}",
            "type": "meeting",
        },
    ]
    events = [{"name": "Daily Standup", "from": "09:00", "to": "09:15", "meet": 1}]
    result = resolve_calendar_rules(rules, events, target_month="Marzo", target_year="2026")
    assert len(result) == 1
    assert result[0]["pid"] == 12
    assert result[0]["pname"] == "Temas internos"
    assert result[0]["task_pattern"] == "Daily - Marzo 2026"
    assert result[0]["type"] == "meeting"
    # Campos originales preservados
    assert result[0]["name"] == "Daily Standup"
    assert result[0]["meet"] == 1


def test_resolve_calendar_rules_no_match():
    """No enriquece evento que no coincide con ningún pattern."""
    rules = [{"pattern": "Daily", "project_id": 12}]
    events = [{"name": "Lunch break", "from": "13:00", "to": "14:00"}]
    result = resolve_calendar_rules(rules, events, target_month="Marzo", target_year="2026")
    assert len(result) == 1
    assert "pid" not in result[0]


def test_resolve_calendar_rules_case_insensitive():
    """El match es case-insensitive."""
    rules = [{"pattern": "daily", "project_id": 12, "task_pattern": "Daily - {month} {year}"}]
    events = [{"name": "DAILY STANDUP", "from": "09:00", "to": "09:15"}]
    result = resolve_calendar_rules(rules, events, target_month="Enero", target_year="2026")
    assert result[0]["pid"] == 12
    assert result[0]["task_pattern"] == "Daily - Enero 2026"


def test_resolve_calendar_rules_first_match_wins():
    """La primera regla que coincide gana."""
    rules = [
        {"pattern": "Daily", "project_id": 12, "project_name": "Regla 1"},
        {"pattern": "Daily", "project_id": 99, "project_name": "Regla 2"},
    ]
    events = [{"name": "Daily Standup"}]
    result = resolve_calendar_rules(rules, events, target_month="Marzo", target_year="2026")
    assert result[0]["pid"] == 12
    assert result[0]["pname"] == "Regla 1"


# --- resolve_app_rules ---


def test_resolve_app_rules_match():
    """Genera mapping para app sin git ctx."""
    rules = [{"app": "Figma", "project_id": 10, "project_name": "Diseño UX"}]
    signals = [{"app": "Figma", "ctx": "", "branch": ""}]
    result = resolve_app_rules(rules, signals)
    assert len(result) == 1
    assert result[0]["ctx"] == "app:Figma"
    assert result[0]["pid"] == 10


def test_resolve_app_rules_skips_git():
    """No genera mapping si la señal tiene ctx tipo git:."""
    rules = [{"app": "Code", "project_id": 10, "project_name": "IDE"}]
    signals = [{"app": "Code", "ctx": "git:org/repo", "branch": "main"}]
    result = resolve_app_rules(rules, signals)
    assert len(result) == 0


def test_resolve_app_rules_case_insensitive():
    """El match de app es case-insensitive."""
    rules = [{"app": "figma", "project_id": 10}]
    signals = [{"app": "Figma", "ctx": ""}]
    result = resolve_app_rules(rules, signals)
    assert len(result) == 1


def test_resolve_app_rules_no_duplicate():
    """No duplica si múltiples señales tienen la misma app."""
    rules = [{"app": "Figma", "project_id": 10}]
    signals = [
        {"app": "Figma", "ctx": ""},
        {"app": "Figma", "ctx": ""},
    ]
    result = resolve_app_rules(rules, signals)
    assert len(result) == 1


# --- resolve_all ---


def test_resolve_all_integration():
    """Resolución completa con todos los tipos de reglas."""
    toml_data = {
        "context_rules": [
            {"ctx": "git:org/repo", "project_id": 5, "project_name": "Proj"},
        ],
        "branch_rules": [
            {"pattern": "mm", "project_id": 3, "project_name": "masmusculo"},
        ],
        "calendar_rules": [
            {"pattern": "Daily", "project_id": 12, "project_name": "Internos",
             "task_pattern": "Daily - {month} {year}", "type": "meeting"},
        ],
        "app_rules": [
            {"app": "Figma", "project_id": 10, "project_name": "Diseño"},
        ],
        "defaults": {
            "project_id": 12,
            "project_name": "Temas internos",
            "confidence": 0.2,
        },
    }
    signals = [
        {"app": "Code", "ctx": "git:org/mm-api", "branch": "feat/mm_545"},
        {"app": "Figma", "ctx": "", "branch": ""},
    ]
    calendar_events = [
        {"name": "Daily Standup", "from": "09:00", "to": "09:15", "meet": 1},
        {"name": "Lunch", "from": "13:00", "to": "14:00"},
    ]

    result = resolve_all(
        toml_data, signals, calendar_events,
        db_mappings=[], branch_task_hints={},
        target_month="Marzo", target_year="2026",
    )

    # extra_mappings: context_rule(1) + branch_rule(1) + app_rule(1) = 3
    assert len(result["extra_mappings"]) == 3

    ctxs = {m["ctx"] for m in result["extra_mappings"]}
    assert "git:org/repo" in ctxs       # context_rule
    assert "git:org/mm-api" in ctxs     # branch_rule
    assert "app:Figma" in ctxs          # app_rule

    # enriched_calendar: Daily enriquecido, Lunch sin cambios
    assert len(result["enriched_calendar"]) == 2
    daily = result["enriched_calendar"][0]
    assert daily["pid"] == 12
    assert daily["task_pattern"] == "Daily - Marzo 2026"
    lunch = result["enriched_calendar"][1]
    assert "pid" not in lunch

    # defaults
    assert result["defaults"]["pid"] == 12
    assert result["defaults"]["confidence"] == 0.2

    # matched_project_ids
    assert result["matched_project_ids"] == {5, 3, 10, 12}


def test_resolve_all_empty_toml():
    """TOML vacío retorna listas vacías."""
    result = resolve_all(
        toml_data={}, signals=[], calendar_events=[],
        db_mappings=[], branch_task_hints={},
        target_month="", target_year="",
    )
    assert result["extra_mappings"] == []
    assert result["enriched_calendar"] == []
    assert result["defaults"] == {}
    assert result["matched_project_ids"] == set()


def test_defaults_passthrough():
    """La sección defaults se pasa tal cual al resultado."""
    toml_data = {
        "defaults": {
            "project_id": 99,
            "project_name": "Fallback",
            "confidence": 0.15,
        },
    }
    result = resolve_all(
        toml_data, signals=[], calendar_events=[],
        db_mappings=[], branch_task_hints={},
        target_month="", target_year="",
    )
    assert result["defaults"] == {"pid": 99, "pname": "Fallback", "confidence": 0.15}


def test_resolve_all_context_rules_override_branch():
    """context_rules tienen prioridad sobre branch_rules para el mismo ctx."""
    toml_data = {
        "context_rules": [
            {"ctx": "git:org/repo", "project_id": 5, "project_name": "Context"},
        ],
        "branch_rules": [
            {"pattern": "repo", "project_id": 99, "project_name": "Branch"},
        ],
    }
    signals = [{"app": "Code", "ctx": "git:org/repo", "branch": "feat/repo_123"}]

    result = resolve_all(
        toml_data, signals, calendar_events=[],
        db_mappings=[], branch_task_hints={},
        target_month="", target_year="",
    )

    # Solo debe haber 1 mapping para git:org/repo, del context_rule
    repo_mappings = [m for m in result["extra_mappings"] if m["ctx"] == "git:org/repo"]
    assert len(repo_mappings) == 1
    assert repo_mappings[0]["pid"] == 5
    assert repo_mappings[0]["pname"] == "Context"
