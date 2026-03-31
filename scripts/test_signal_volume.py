#!/usr/bin/env python3
"""Test de volumen de senales para medir rendimiento de generacion.

Genera senales simuladas, las compacta en spans (mismo algoritmo que el daemon)
e invoca claude --print para medir tiempos. No requiere daemon ni DB real.

Uso:
    # Solo medir payload (sin invocar claude)
    python3 scripts/test_signal_volume.py --dry-run

    # Probar con un volumen especifico
    python3 scripts/test_signal_volume.py --signals 925

    # Probar varios volumenes (sweep)
    python3 scripts/test_signal_volume.py --sweep

    # Comparar compactacion normal vs agresiva
    python3 scripts/test_signal_volume.py --compare --sweep

    # Usar agente externo (repo clonado)
    python3 scripts/test_signal_volume.py --agent-repo /tmp/agentes-imputacion

    # Cambiar modelo
    python3 scripts/test_signal_volume.py --model sonnet

    # Test completo: agresivo, 925 senales, historial, gitlab, calendar, repo agentes
    python3 scripts/test_signal_volume.py --signals 925 --aggressive --rich --agent-repo /tmp/agentes-imputacion

    # Comparar modelos
    python3 scripts/test_signal_volume.py --signals 925 --aggressive --rich --compare-models
"""
import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# --- Datos simulados realistas ---

PROJECTS = ["mimir-app", "gextia", "odoo-addons", "infra-deploy", "portal-web"]

BRANCHES = {
    "mimir-app": ["main", "feat/signals", "feat/discover-filters", "fix/timeout"],
    "gextia": ["main", "gextia_8119", "gextia_8205", "feat/stock-migration"],
    "odoo-addons": ["16.0", "16.0-fix/invoice", "16.0-feat/report"],
    "infra-deploy": ["main", "feat/k8s-config"],
    "portal-web": ["main", "feat/login-redesign", "fix/css-responsive"],
}

# (app, context_template, weight)
APPS = [
    ("code", "git:/home/user/projects/{project}", 40),
    ("terminal", "git:/home/user/projects/{project}", 15),
    ("firefox", "web:github.com", 10),
    ("firefox", "web:docs.python.org", 5),
    ("firefox", "web:stackoverflow.com", 5),
    ("Google Chrome", "web:gitlab.factorlibre.com", 8),
    ("Google Chrome", "web:odoo.factorlibre.com", 4),
    ("slack", "app:slack", 8),
    ("nautilus", "app:nautilus", 2),
]

WINDOW_TITLES = {
    "code": [
        "models.py - {project} - Visual Studio Code",
        "views.py - {project} - Visual Studio Code",
        "test_api.py - {project} - Visual Studio Code",
        "README.md - {project} - Visual Studio Code",
        "settings.json - {project} - Visual Studio Code",
        "__init__.py - {project} - Visual Studio Code",
        "router.py - {project} - Visual Studio Code",
        "schema.sql - {project} - Visual Studio Code",
        "Dockerfile - {project} - Visual Studio Code",
        "package.json - {project} - Visual Studio Code",
    ],
    "firefox": [
        "Pull Request #42 - GitHub",
        "Issues - {project} - GitHub",
        "Python documentation - Mozilla Firefox",
        "Stack Overflow - How to fix async timeout",
        "Odoo 16 Documentation",
    ],
    "Google Chrome": [
        "MR !301 Migracion stock - GitLab",
        "Pipeline #45678 passed - GitLab",
        "Odoo - Timesheets",
        "Odoo - Proyectos",
        "GitLab - Issues Board",
        "Google Meet - Refinamiento",
    ],
    "slack": [
        "Slack | #desarrollo",
        "Slack | #general",
        "Slack | @manager - DM",
    ],
    "terminal": [
        "user@dev: ~/projects/{project}",
        "pytest tests/ -v",
        "git log --oneline",
        "docker compose up -d",
    ],
    "nautilus": ["Archivos - Descargas", "Archivos - Documentos"],
    "zoom": ["Zoom Meeting - Daily Standup", "Zoom Meeting - Refinamiento Sprint"],
    "Google Meet": ["Google Meet - Daily Standup", "Google Meet - Refinamiento"],
}

CALENDAR_EVENTS_POOL = [
    ("Daily Standup", 15, True),
    ("Refinamiento Sprint", 60, True),
    ("1:1 con Manager", 30, True),
    ("Demo Sprint", 45, True),
    ("Formacion interna", 90, True),
    ("Revision codigo equipo", 30, True),
]

# Proyectos Odoo simulados
ODOO_PROJECTS = [
    {"id": 1, "name": "Mimir"},
    {"id": 2, "name": "Gextia"},
    {"id": 3, "name": "Odoo Addons FactorLibre"},
    {"id": 4, "name": "Infraestructura"},
    {"id": 5, "name": "Portal Web"},
    {"id": 6, "name": "Temas internos"},
    {"id": 7, "name": "connector-prestashop"},
]

ODOO_TASKS = {
    "1": [{"id": 101, "name": "Desarrollo Mimir v0.9"}, {"id": 102, "name": "Testing Mimir"}],
    "2": [{"id": 201, "name": "8119 - Migracion modulo stock"}, {"id": 202, "name": "8205 - Fix facturas"}],
    "3": [{"id": 301, "name": "Modulo invoice"}, {"id": 302, "name": "Modulo report"}],
    "4": [{"id": 401, "name": "Mantenimiento servidores"}],
    "5": [{"id": 501, "name": "Rediseno login"}],
    "6": [{"id": 601, "name": "Daily - Marzo 2026"}, {"id": 602, "name": "Refinamiento - Marzo 2026"},
          {"id": 603, "name": "Formacion impulsada - Marzo 2026"}],
    "7": [{"id": 701, "name": "442 - Sincronizacion precios"}],
}

# Historial de navegador simulado
BROWSER_HISTORY = [
    {"domain": "gitlab.factorlibre.com", "visits": 45, "from": "08:15", "to": "17:30",
     "titles": ["MR !301 Migracion stock", "Pipeline #45678", "Issues Board - Gextia", "Merge Requests", "CI/CD Jobs"]},
    {"domain": "github.com", "visits": 28, "from": "08:30", "to": "16:45",
     "titles": ["Mimir-App/mimir-app - Issues", "Pull Request #17", "Actions - Build", "Code - blocks.rs"]},
    {"domain": "odoo.factorlibre.com", "visits": 15, "from": "09:00", "to": "17:00",
     "titles": ["Timesheets", "Proyectos - Gextia", "Tareas", "Facturacion"]},
    {"domain": "docs.python.org", "visits": 12, "from": "10:00", "to": "14:30",
     "titles": ["asyncio - Event Loop", "sqlite3 - DB-API", "typing - Type Hints"]},
    {"domain": "stackoverflow.com", "visits": 18, "from": "08:45", "to": "16:00",
     "titles": ["SQLite WAL mode concurrent access", "Python asyncio gather timeout", "Vue 3 reactive Map"]},
    {"domain": "meet.google.com", "visits": 4, "from": "09:00", "to": "15:30",
     "titles": ["Daily Standup", "Refinamiento Sprint"]},
    {"domain": "mail.google.com", "visits": 8, "from": "08:30", "to": "17:00",
     "titles": ["Inbox", "RE: Deploy viernes", "FW: Presupuesto Q2"]},
    {"domain": "slack.com", "visits": 6, "from": "08:00", "to": "17:30",
     "titles": ["#desarrollo", "#general"]},
    {"domain": "linear.app", "visits": 5, "from": "09:30", "to": "16:00",
     "titles": ["MIR-42 Fix timeout", "MIR-38 Discover filters", "Sprint Board"]},
    {"domain": "console.cloud.google.com", "visits": 3, "from": "11:00", "to": "12:00",
     "titles": ["Cloud Run - mimir-api", "Logs Explorer"]},
]

# Eventos GitLab simulados (realistas para un dia de trabajo)
GITLAB_EVENTS_RICH = [
    {"t": "08:45", "type": "pushed to", "target": "MergeRequest",
     "title": "feat: migrar modelo stock.move a v16", "iid": 891, "pid": 15,
     "push": {"ref": "gextia_8119", "action": "pushed to", "commits": 2}},
    {"t": "09:30", "type": "pushed to", "target": "MergeRequest",
     "title": "feat: agregar filtros Discover", "iid": 456, "pid": 8,
     "push": {"ref": "feat/discover-filters", "action": "pushed to", "commits": 1}},
    {"t": "10:15", "type": "commented on", "target": "MergeRequest",
     "title": "fix: sincronizacion precios Prestashop", "iid": 342, "pid": 22},
    {"t": "10:50", "type": "pushed to", "target": "MergeRequest",
     "title": "feat: migrar modelo stock.move a v16", "iid": 891, "pid": 15,
     "push": {"ref": "gextia_8119", "action": "pushed to", "commits": 3}},
    {"t": "11:30", "type": "opened", "target": "Issue",
     "title": "Error en calculo de stock reservado", "iid": 1205, "pid": 15},
    {"t": "12:00", "type": "accepted", "target": "MergeRequest",
     "title": "fix: correccion informe contable", "iid": 340, "pid": 15},
    {"t": "14:45", "type": "pushed to", "target": "MergeRequest",
     "title": "feat: migrar modelo stock.move a v16", "iid": 891, "pid": 15,
     "push": {"ref": "gextia_8119", "action": "pushed to", "commits": 4}},
    {"t": "15:30", "type": "commented on", "target": "MergeRequest",
     "title": "feat: migrar modelo stock.move a v16", "iid": 891, "pid": 15},
    {"t": "16:00", "type": "pushed to", "target": "MergeRequest",
     "title": "fix: responsive layout portal", "iid": 567, "pid": 30,
     "push": {"ref": "fix/css-responsive", "action": "pushed to", "commits": 1}},
    {"t": "16:30", "type": "closed", "target": "Issue",
     "title": "Bug en exportacion CSV", "iid": 1190, "pid": 15},
]

GITHUB_EVENTS_RICH = [
    {"t": "09:20", "type": "push", "title": "feat/signals", "repo": "Mimir-App/mimir-app"},
    {"t": "10:30", "type": "issue_comment", "title": "Fix timeout in generation #17",
     "repo": "Mimir-App/mimir-app", "id": 17},
    {"t": "14:30", "type": "push", "title": "feat/discover-filters", "repo": "Mimir-App/mimir-app"},
    {"t": "16:15", "type": "pull_request", "title": "Add aggressive signal compaction",
     "repo": "Mimir-App/mimir-app", "id": 18},
]

CALENDAR_EVENTS_RICH = [
    {"name": "Daily Standup", "from": "09:00", "to": "09:15", "meet": 1},
    {"name": "Refinamiento Sprint 42", "from": "11:00", "to": "12:00", "meet": 1},
    {"name": "1:1 con Manager", "from": "15:30", "to": "16:00", "meet": 1},
]


def generate_signals(date: str, count: int) -> list[dict]:
    """Genera senales simuladas realistas para un dia de trabajo."""
    signals = []
    base = datetime.strptime(date, "%Y-%m-%d")

    work_start = base.replace(hour=8, minute=0)
    lunch_start = base.replace(hour=13, minute=30)
    lunch_end = base.replace(hour=14, minute=30)
    work_end = base.replace(hour=18, minute=0)

    effective_seconds = 28800
    interval_s = max(10, effective_seconds // count)
    interval = timedelta(seconds=interval_s)

    current = work_start
    current_project = random.choice(PROJECTS)
    current_branch = random.choice(BRANCHES[current_project])
    context_switch_at = current + timedelta(minutes=random.randint(15, 45))

    # Reuniones
    meetings = [
        (base.replace(hour=9, minute=0), base.replace(hour=9, minute=15), "Daily Standup"),
        (base.replace(hour=11, minute=0), base.replace(hour=12, minute=0), "Refinamiento Sprint 42"),
        (base.replace(hour=15, minute=30), base.replace(hour=16, minute=0), "1:1 con Manager"),
    ]

    apps_flat = []
    for app, ctx, weight in APPS:
        apps_flat.extend([(app, ctx)] * weight)

    generated = 0
    while generated < count:
        if lunch_start <= current < lunch_end:
            current = lunch_end
            continue
        if current >= work_end:
            current = work_start + timedelta(seconds=random.randint(0, 100))

        if current >= context_switch_at:
            current_project = random.choice(PROJECTS)
            current_branch = random.choice(BRANCHES[current_project])
            context_switch_at = current + timedelta(minutes=random.randint(15, 45))

        in_meeting = False
        meeting_event = None
        for m_start, m_end, m_name in meetings:
            if m_start <= current < m_end:
                in_meeting = True
                meeting_event = m_name
                break

        if in_meeting:
            app = random.choice(["zoom", "Google Meet"])
            ctx = f"meeting:{meeting_event}"
            branch = ""
        else:
            app, ctx_tpl = random.choice(apps_flat)
            if "{project}" in ctx_tpl:
                ctx = ctx_tpl.format(project=current_project)
                branch = current_branch
            else:
                ctx = ctx_tpl
                branch = ""

        titles = WINDOW_TITLES.get(app, ["Unknown"])
        title = random.choice(titles).format(project=current_project)
        idle_ms = 0 if random.random() > 0.1 else random.randint(5000, 60000)

        signal = {
            "timestamp": current.strftime("%Y-%m-%dT%H:%M:%S.000000+00:00"),
            "app_name": app,
            "window_title": title,
            "context_key": ctx,
            "git_branch": branch if branch else None,
            "is_meeting": 1 if in_meeting else 0,
            "calendar_event": meeting_event,
            "idle_ms": idle_ms,
        }
        signals.append(signal)
        generated += 1
        current += interval

    return signals


def compact_signals(signals: list[dict]) -> list[dict]:
    """Compacta senales en spans (mismo algoritmo que blocks.py)."""
    spans: list[dict] = []
    for s in signals:
        t = s["timestamp"][11:16]
        app = s.get("app_name", "")
        ctx = s.get("context_key", "")
        branch = s.get("git_branch") or ""
        meet = s.get("is_meeting", 0)
        cal = s.get("calendar_event") or ""
        title = (s.get("window_title") or "")[:80]

        parts = t.split(":")
        t_min = int(parts[0]) * 60 + int(parts[1])

        if spans:
            cur = spans[-1]
            cur_end_parts = cur["to"].split(":")
            cur_end_min = int(cur_end_parts[0]) * 60 + int(cur_end_parts[1])
            same_group = (
                cur.get("app") == app
                and cur.get("ctx") == ctx
                and cur.get("branch") == branch
                and cur.get("meet") == meet
                and (t_min - cur_end_min) <= 5
            )
            if same_group:
                cur["to"] = t
                cur["n"] += 1
                if title and title not in cur["_titles_set"]:
                    cur["_titles_set"].add(title)
                    cur["titles"].append(title)
                if cal and not cur.get("cal"):
                    cur["cal"] = cal
                continue

        span = {
            "from": t, "to": t, "app": app, "n": 1,
            "ctx": ctx, "branch": branch, "meet": meet, "cal": cal,
            "titles": [title] if title else [],
            "_titles_set": {title} if title else set(),
        }
        spans.append(span)

    compact = []
    for sp in spans:
        del sp["_titles_set"]
        sp["titles"] = sp["titles"][:5]
        cleaned = {k: v for k, v in sp.items() if v not in (None, "", 0, [])}
        cleaned["from"] = sp["from"]
        cleaned["to"] = sp["to"]
        cleaned["n"] = sp["n"]
        compact.append(cleaned)
    return compact


def aggressive_compact(spans: list[dict]) -> list[dict]:
    """Segunda pasada: agrupa spans por ctx+branch, ignorando gaps temporales."""
    groups: dict[str, dict] = {}

    for sp in spans:
        ctx = sp.get("ctx", "")
        branch = sp.get("branch", "")
        key = f"{ctx}|{branch}"

        if key not in groups:
            groups[key] = {
                "ctx": ctx, "branch": branch, "app": sp.get("app", ""),
                "apps": {}, "first": sp["from"], "last": sp["to"],
                "total_signals": 0, "intervals": [],
                "titles": set(), "meet": sp.get("meet", 0), "cal": sp.get("cal", ""),
            }

        g = groups[key]
        g["total_signals"] += sp["n"]
        g["last"] = sp["to"]

        app = sp.get("app", "")
        if app:
            g["apps"][app] = g["apps"].get(app, 0) + sp["n"]

        g["intervals"].append((sp["from"], sp["to"]))

        for t in sp.get("titles", []):
            if len(g["titles"]) < 5:
                g["titles"].add(t)

        if sp.get("meet"):
            g["meet"] = 1
        if sp.get("cal") and not g["cal"]:
            g["cal"] = sp["cal"]

    result = []
    for key, g in groups.items():
        intervals = sorted(g["intervals"])
        merged = []
        for start, end in intervals:
            if merged and _time_diff_min(merged[-1][1], start) <= 30:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        ranges = [f"{s}-{e}" if s != e else s for s, e in merged]

        entry: dict = {
            "ctx": g["ctx"], "n": g["total_signals"],
            "from": g["first"], "to": g["last"], "ranges": ranges,
        }

        if g["branch"]:
            entry["branch"] = g["branch"]
        if len(g["apps"]) > 1:
            entry["apps"] = g["apps"]
        elif g["app"]:
            entry["app"] = g["app"]
        if g["titles"]:
            entry["titles"] = list(g["titles"])[:5]
        if g["meet"]:
            entry["meet"] = 1
        if g["cal"]:
            entry["cal"] = g["cal"]

        result.append(entry)

    result.sort(key=lambda x: x.get("from", ""))
    return result


def _time_diff_min(t1: str, t2: str) -> int:
    h1, m1 = map(int, t1.split(":"))
    h2, m2 = map(int, t2.split(":"))
    return (h2 * 60 + m2) - (h1 * 60 + m1)


def build_generation_data(date: str, compact_spans: list[dict], rich: bool = False) -> dict:
    """Construye un payload de generation-data simulado."""
    if rich:
        gitlab_events = GITLAB_EVENTS_RICH
        github_events = GITHUB_EVENTS_RICH
        calendar_events = CALENDAR_EVENTS_RICH
    else:
        gitlab_events = [
            {"t": "09:30", "type": "PushEvent", "target": "push",
             "title": "feat: update stock migration", "push": {"ref": "gextia_8119", "commits": 3}},
        ]
        github_events = [
            {"t": "10:00", "type": "push", "title": "feat/signals", "repo": "MimirOrg/mimir-app"},
        ]
        calendar_events = [
            {"name": "Daily Standup", "from": "09:00", "to": "09:15", "meet": 1},
        ]

    context_mappings = [
        {"ctx": "git:/home/user/projects/mimir-app", "pid": 1, "tid": 101},
        {"ctx": "git:/home/user/projects/gextia", "pid": 2, "tid": 201},
        {"ctx": "git:/home/user/projects/odoo-addons", "pid": 3},
        {"ctx": "git:/home/user/projects/portal-web", "pid": 5},
        {"ctx": "meeting:Daily Standup", "pid": 6, "tid": 601},
        {"ctx": "meeting:Refinamiento Sprint 42", "pid": 6, "tid": 602},
        {"ctx": "meeting:1:1 con Manager", "pid": 6, "tid": 603},
    ]

    branch_task_hints = {"gextia": ["8119", "8205"], "prestashop": ["442"]}

    result = {
        "date": date,
        "signals": compact_spans,
        "gitlab_events": gitlab_events,
        "github_events": github_events,
        "calendar_events": calendar_events,
        "projects": ODOO_PROJECTS,
        "tasks_by_project": ODOO_TASKS,
        "preserved_blocks": [],
        "context_mappings": context_mappings,
        "branch_task_hints": branch_task_hints,
    }

    if rich:
        result["browser_history"] = BROWSER_HISTORY

    return result


def find_agent_prompt(agent_repo: str | None) -> str:
    """Busca el system prompt del agente generador."""
    # Prioridad: repo externo > built-in
    if agent_repo:
        repo_agent = Path(agent_repo) / "timesheet-generator.md"
        if repo_agent.exists():
            return repo_agent.read_text()

    built_in = Path(__file__).parent.parent / ".claude/agents/timesheet-generator.md"
    if built_in.exists():
        return built_in.read_text()

    raise FileNotFoundError("No se encontro timesheet-generator.md")


def measure_claude(generation_data: dict, date: str, model: str = "haiku",
                   agent_repo: str | None = None) -> dict:
    """Invoca claude --print y mide el tiempo."""
    try:
        system_prompt = find_agent_prompt(agent_repo)
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Si hay repo, anadir CLAUDE.md como contexto extra
    if agent_repo:
        claude_md = Path(agent_repo) / "CLAUDE.md"
        if claude_md.exists():
            system_prompt += f"\n\n## Contexto del repositorio de agentes\n\n{claude_md.read_text()}"
        # Tambien anadir rules si existen
        rules_path = Path(agent_repo) / "config" / "timesheet-rules.example.md"
        if rules_path.exists():
            system_prompt += f"\n\n## Reglas de matching del usuario\n\n{rules_path.read_text()}"

    data_json = json.dumps(generation_data, ensure_ascii=False)
    prompt = (
        f"Genera bloques para {date}. NO ejecutes comandos. "
        f"Devuelve SOLO JSON. Datos:\n\n{data_json}"
    )

    mcp_path = "/tmp/mimir-empty-mcp.json"
    Path(mcp_path).write_text('{"mcpServers":{}}')

    cmd = [
        "claude",
        "--print",
        "--no-session-persistence",
        "--system-prompt", system_prompt,
        "--permission-mode", "plan",
        "--model", model,
        "--disable-slash-commands",
        "--mcp-config", mcp_path,
        "-p", prompt,
    ]

    # Si hay repo, usar como cwd
    cwd = agent_repo if agent_repo and Path(agent_repo).is_dir() else None

    n_items = len(generation_data.get("signals", []))
    prompt_kb = round(len(prompt) / 1024, 1)
    system_kb = round(len(system_prompt) / 1024, 1)
    print(f"  Invocando claude --model {model} ({n_items} items, prompt={prompt_kb} KB, system={system_kb} KB)...")

    start = time.time()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=cwd)
        elapsed = time.time() - start

        json_ok = False
        blocks_count = 0
        blocks_data = None
        try:
            idx = result.stdout.find("{")
            if idx >= 0:
                depth = 0
                end_idx = idx
                for i, c in enumerate(result.stdout[idx:], idx):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end_idx = i + 1
                            break
                parsed = json.loads(result.stdout[idx:end_idx])
                json_ok = True
                blocks_data = parsed.get("blocks", [])
                blocks_count = len(blocks_data)
        except (json.JSONDecodeError, ValueError):
            pass

        res = {
            "elapsed_s": round(elapsed, 1),
            "exit_code": result.returncode,
            "stdout_len": len(result.stdout),
            "json_valid": json_ok,
            "blocks_generated": blocks_count,
            "model": model,
        }

        # Resumen de bloques si hay
        if blocks_data:
            total_min = sum(b.get("duration_minutes", 0) for b in blocks_data)
            with_project = sum(1 for b in blocks_data if b.get("odoo_project_id"))
            with_task = sum(1 for b in blocks_data if b.get("odoo_task_id"))
            avg_conf = sum(b.get("confidence", 0) for b in blocks_data) / max(len(blocks_data), 1)
            types = {}
            for b in blocks_data:
                t = b.get("type", "unknown")
                types[t] = types.get(t, 0) + 1
            res["total_hours"] = round(total_min / 60, 1)
            res["with_project"] = with_project
            res["with_task"] = with_task
            res["avg_confidence"] = round(avg_conf, 2)
            res["types"] = types

        if result.stderr:
            res["stderr_snippet"] = result.stderr[:300]

        return res
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        return {"error": f"TIMEOUT tras {round(elapsed, 1)}s", "elapsed_s": round(elapsed, 1), "model": model}
    except FileNotFoundError:
        return {"error": "claude CLI no encontrado"}


def run_test(num_signals: int, date: str, dry_run: bool,
             use_aggressive: bool = False, rich: bool = False,
             model: str = "haiku", agent_repo: str | None = None) -> dict:
    """Ejecuta un test completo para un volumen de senales."""
    mode = "AGRESIVA" if use_aggressive else "NORMAL"
    extras = []
    if rich:
        extras.append("rich")
    if agent_repo:
        extras.append(f"repo:{Path(agent_repo).name}")
    extra_str = f" +{'+'.join(extras)}" if extras else ""

    print(f"\n{'='*60}")
    print(f"TEST: {num_signals} senales [{mode}] modelo={model}{extra_str}")
    print(f"{'='*60}")

    # 1. Generar senales
    print(f"  Generando {num_signals} senales simuladas...")
    signals = generate_signals(date, num_signals)

    # 2. Compactar
    spans = compact_signals(signals)
    ratio1 = round(num_signals / max(len(spans), 1), 1)
    print(f"  Pasada 1: {len(signals)} senales -> {len(spans)} spans ({ratio1}x)")

    if use_aggressive:
        final_spans = aggressive_compact(spans)
        ratio2 = round(num_signals / max(len(final_spans), 1), 1)
        print(f"  Pasada 2: {len(spans)} spans -> {len(final_spans)} grupos ({ratio2}x total)")
    else:
        final_spans = spans

    # 3. Construir payload
    gen_data = build_generation_data(date, final_spans, rich=rich)
    payload_json = json.dumps(gen_data, ensure_ascii=False)
    payload_kb = round(len(payload_json) / 1024, 1)
    approx_tokens = round(len(payload_json) / 4)

    print(f"\n  === Payload ===")
    print(f"  Items en signals: {len(final_spans)}")
    print(f"  JSON total: {payload_kb} KB")
    print(f"  Tokens aprox: ~{approx_tokens}")

    for key in ["signals", "gitlab_events", "github_events", "calendar_events",
                 "projects", "tasks_by_project", "context_mappings", "browser_history"]:
        val = gen_data.get(key)
        if val:
            size = len(json.dumps(val, ensure_ascii=False))
            items = len(val)
            print(f"    {key}: {items} items, {round(size/1024, 1)} KB")

    result = {
        "signals_raw": num_signals,
        "spans": len(final_spans),
        "ratio": round(num_signals / max(len(final_spans), 1), 1),
        "payload_kb": payload_kb,
        "approx_tokens": approx_tokens,
        "mode": mode,
        "model": model,
    }

    # 4. Invocar Claude
    if not dry_run:
        print(f"\n  === Claude CLI ===")
        claude_result = measure_claude(gen_data, date, model=model, agent_repo=agent_repo)
        if "error" in claude_result:
            print(f"  ERROR: {claude_result['error']}")
        else:
            print(f"  Tiempo: {claude_result['elapsed_s']}s")
            print(f"  Exit code: {claude_result['exit_code']}")
            print(f"  JSON valido: {claude_result['json_valid']}")
            print(f"  Bloques: {claude_result['blocks_generated']}")
            if claude_result.get("total_hours") is not None:
                print(f"  Horas totales: {claude_result['total_hours']}h")
                print(f"  Con proyecto: {claude_result['with_project']}/{claude_result['blocks_generated']}")
                print(f"  Con tarea: {claude_result['with_task']}/{claude_result['blocks_generated']}")
                print(f"  Confidence media: {claude_result['avg_confidence']}")
                print(f"  Tipos: {claude_result['types']}")
        result.update(claude_result)

    return result


def main():
    parser = argparse.ArgumentParser(description="Test de volumen de senales")
    parser.add_argument("--signals", type=int, default=925)
    parser.add_argument("--date", default="2026-03-28")
    parser.add_argument("--dry-run", action="store_true",
                        help="Solo medir payload, no invocar claude")
    parser.add_argument("--sweep", action="store_true",
                        help="Probar volumenes: 100, 300, 500, 700, 925")
    parser.add_argument("--aggressive", action="store_true",
                        help="Usar compactacion agresiva (segunda pasada)")
    parser.add_argument("--rich", action="store_true",
                        help="Datos ricos: mas gitlab, github, calendar, browser history")
    parser.add_argument("--model", default="haiku",
                        help="Modelo Claude (haiku, sonnet, opus)")
    parser.add_argument("--agent-repo", default=None,
                        help="Ruta al repo de agentes (ej: /tmp/agentes-imputacion)")
    parser.add_argument("--compare", action="store_true",
                        help="Comparar normal vs agresiva (solo payload)")
    parser.add_argument("--compare-models", action="store_true",
                        help="Comparar haiku vs sonnet vs opus")
    args = parser.parse_args()

    # Modo comparacion payload
    if args.compare:
        volumes = [100, 300, 500, 700, 925] if args.sweep else [args.signals]
        results = []
        for vol in volumes:
            rn = run_test(vol, args.date, dry_run=True, use_aggressive=False, rich=args.rich)
            ra = run_test(vol, args.date, dry_run=True, use_aggressive=True, rich=args.rich)
            results.append((rn, ra))

        print(f"\n\n{'='*60}")
        print("COMPARACION: Normal vs Agresiva")
        print(f"{'='*60}")
        print(f"{'Senales':>8} {'Spans N':>8} {'Spans A':>8} {'KB N':>6} {'KB A':>6} {'Tok N':>7} {'Tok A':>7} {'Reduc':>7}")
        print(f"{'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7}")
        for rn, ra in results:
            reduction = round((1 - ra["approx_tokens"] / max(rn["approx_tokens"], 1)) * 100, 1)
            print(
                f"{rn['signals_raw']:>8} {rn['spans']:>8} {ra['spans']:>8} "
                f"{rn['payload_kb']:>6} {ra['payload_kb']:>6} "
                f"{rn['approx_tokens']:>7} {ra['approx_tokens']:>7} "
                f"{reduction:>6}%"
            )
        return

    # Modo comparacion modelos
    if args.compare_models:
        models = ["haiku", "sonnet"]
        results = []
        for model in models:
            r = run_test(args.signals, args.date, dry_run=False,
                         use_aggressive=args.aggressive, rich=args.rich,
                         model=model, agent_repo=args.agent_repo)
            results.append(r)

        print(f"\n\n{'='*60}")
        print("COMPARACION MODELOS")
        print(f"{'='*60}")
        print(f"{'Modelo':>8} {'Spans':>6} {'Tiempo':>8} {'Bloques':>8} {'Horas':>6} {'Conf':>6} {'JSON':>5}")
        print(f"{'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*5}")
        for r in results:
            ct = r.get("elapsed_s", "-")
            bl = r.get("blocks_generated", "-")
            hrs = r.get("total_hours", "-")
            conf = r.get("avg_confidence", "-")
            ok = "Y" if r.get("json_valid") else "N" if "elapsed_s" in r else "?"
            print(
                f"{r['model']:>8} {r['spans']:>6} {str(ct):>7}s "
                f"{str(bl):>8} {str(hrs):>6} {str(conf):>6} {ok:>5}"
            )
        return

    # Ejecucion normal
    volumes = [100, 300, 500, 700, 925] if args.sweep else [args.signals]
    results = []

    for vol in volumes:
        r = run_test(vol, args.date, args.dry_run,
                     use_aggressive=args.aggressive, rich=args.rich,
                     model=args.model, agent_repo=args.agent_repo)
        results.append(r)

    # Resumen tabla
    if len(results) > 1:
        print(f"\n\n{'='*60}")
        print(f"RESUMEN [{results[0].get('mode', '?')}] modelo={args.model}")
        print(f"{'='*60}")
        hdr = f"{'Senales':>8} {'Spans':>6} {'Ratio':>6} {'KB':>7} {'Tokens':>7}"
        sep = f"{'-'*8} {'-'*6} {'-'*6} {'-'*7} {'-'*7}"
        if not args.dry_run:
            hdr += f" {'Tiempo':>8} {'Bloques':>8} {'Horas':>6} {'OK':>4}"
            sep += f" {'-'*8} {'-'*8} {'-'*6} {'-'*4}"
        print(hdr)
        print(sep)
        for r in results:
            line = (
                f"{r['signals_raw']:>8} {r['spans']:>6} "
                f"{r['ratio']:>5}x {r['payload_kb']:>6} {r['approx_tokens']:>7}"
            )
            if not args.dry_run:
                ct = r.get("elapsed_s", "-")
                bl = r.get("blocks_generated", "-")
                hrs = r.get("total_hours", "-")
                ok = "Y" if r.get("json_valid") else "N" if "elapsed_s" in r else "?"
                line += f" {str(ct):>7}s {str(bl):>8} {str(hrs):>6} {ok:>4}"
            print(line)


if __name__ == "__main__":
    main()
