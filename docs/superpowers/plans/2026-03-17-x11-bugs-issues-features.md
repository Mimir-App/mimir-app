# Bugs X11 + Features Issues + Popup Timesheets — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 bugs (Google Calendar text, Odoo timezone, X11 capture diagnostics) and add 4 features (issue score manual, search/follow issues, configurable priority labels, issue detail popup, timesheet edit popup).

**Architecture:** 3 sprints incrementales. Sprint 1 arregla bugs existentes. Sprint 2 agrega tabla `issue_preferences` en SQLite + 6 endpoints nuevos en FastAPI + componentes Vue. Sprint 3 agrega popup de edicion de timesheets con 1 endpoint nuevo.

**Tech Stack:** Python 3.10+ (FastAPI, aiosqlite), Rust (Tauri 2), Vue 3 + TypeScript, SQLite WAL, marked + DOMPurify (npm).

---

## File Structure

### Files to modify

| File | Changes |
|------|---------|
| `src/views/SettingsView.vue` | Fix Google Calendar text (line 764), add priority labels config in GitLab tab |
| `daemon/mimir_daemon/integrations/odoo_v11.py` | Fix timezone in get_today_attendance() |
| `daemon/mimir_daemon/integrations/odoo_v16.py` | Fix timezone in get_today_attendance() |
| `daemon/mimir_daemon/platform/linux.py` | X11 startup diagnostic, ERROR log level |
| `daemon/mimir_daemon/db.py` | Add issue_preferences table + CRUD methods |
| `daemon/mimir_daemon/server.py` | 7 new endpoints + modify GET /odoo/entries |
| `daemon/mimir_daemon/sources/gitlab.py` | search_issues(), get_issue_notes(), get_labels() |
| `src-tauri/src/commands/daemon.rs` | 7 new Tauri proxy commands |
| `src-tauri/src/commands/config.rs` | Sync missing fields in AppConfig struct |
| `src-tauri/src/lib.rs` | Register 7 new commands |
| `src/lib/api.ts` | 7 new API methods |
| `src/lib/types.ts` | Update AppConfig, add IssuePreference type |
| `src/lib/scoring.ts` | Dynamic priority labels from config |
| `src/stores/issues.ts` | Preferences merge, followed issues, search |
| `src/stores/timesheets.ts` | Selected entry for edit modal |
| `src/views/IssuesView.vue` | Search bar, filter tabs, click handler |
| `src/views/TimesheetsView.vue` | Click handler for edit modal |
| `src/components/issues/IssueTable.vue` | Click handler, inline score edit |
| `daemon/tests/test_server.py` | Tests for new endpoints |
| `daemon/tests/test_gitlab_source.py` | Tests for search, notes, labels |
| `daemon/tests/test_odoo_v11.py` | Test timezone fix |
| `daemon/tests/test_odoo_v16.py` | Test timezone fix |

### Files to create

| File | Purpose |
|------|---------|
| `src/components/issues/IssueDetailModal.vue` | Popup detalle de issue |
| `src/components/timesheets/TimesheetEditModal.vue` | Popup edicion timesheet |

---

## Chunk 1: Sprint 1 — Bug Fixes

### Task 1: Fix Google Calendar text

**Files:**
- Modify: `src/views/SettingsView.vue:764`

- [ ] **Step 1: Fix text**

In `src/views/SettingsView.vue` line 764, change:
```html
<template v-else>Configura Client ID y Secret en la pestaña Captura</template>
```
to:
```html
<template v-else>Configura Client ID y Secret en la pestaña Google</template>
```

- [ ] **Step 2: Verify**

Run: `npx vue-tsc --noEmit`
Expected: No errors

---

### Task 2: Fix Odoo timezone offset

**Files:**
- Modify: `daemon/mimir_daemon/integrations/odoo_v16.py:266-296`
- Modify: `daemon/mimir_daemon/integrations/odoo_v11.py:229-259`
- Test: `daemon/tests/test_odoo_v16.py`, `daemon/tests/test_odoo_v11.py`

- [ ] **Step 1: Write failing test for v16**

In `daemon/tests/test_odoo_v16.py`, add:

```python
@pytest.mark.asyncio
async def test_get_today_attendance_uses_local_timezone(odoo_v16_client, mock_response):
    """get_today_attendance usa timezone local para determinar 'hoy'."""
    import zoneinfo
    from unittest.mock import patch
    from datetime import datetime, timezone

    # Simular que son las 00:30 en Madrid (23:30 UTC del dia anterior)
    fake_utc = datetime(2026, 3, 17, 23, 30, 0, tzinfo=timezone.utc)
    # En Madrid (UTC+1 invierno) eso es 2026-03-18 00:30
    with patch("daemon.mimir_daemon.integrations.odoo_v16.datetime") as mock_dt:
        mock_dt.now.return_value = fake_utc
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mock_response({"result": []})
        result = await odoo_v16_client.get_today_attendance()

    # Debe buscar con fecha 2026-03-18 (hora local), no 2026-03-17 (UTC)
    call_args = mock_response.call_args
    assert "2026-03-18" in str(call_args) or result is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daemon && python -m pytest tests/test_odoo_v16.py::test_get_today_attendance_uses_local_timezone -v`
Expected: FAIL

- [ ] **Step 3: Implement timezone fix in odoo_v16.py**

In `daemon/mimir_daemon/integrations/odoo_v16.py`, modify `get_today_attendance()` (line 266):

```python
async def get_today_attendance(self) -> dict[str, Any] | None:
    """Obtiene el attendance de hoy del empleado."""
    from datetime import datetime, timezone
    import zoneinfo

    # Usar timezone del usuario para determinar "hoy"
    user_tz = zoneinfo.ZoneInfo(self._timezone)
    today = datetime.now(user_tz).strftime("%Y-%m-%d")
    domain = [
        ("employee_id", "=", self._employee_id),
        ("check_in", ">=", f"{today} 00:00:00"),
        ("check_in", "<=", f"{today} 23:59:59"),
    ]
```

The `self._timezone` needs to be passed in `__init__`. Modify `__init__` to accept `timezone: str = "Europe/Madrid"` and store as `self._timezone`.

- [ ] **Step 4: Apply same fix to odoo_v11.py**

Same pattern: add `timezone` param to `__init__`, use `zoneinfo.ZoneInfo` in `get_today_attendance()`.

- [ ] **Step 5: Update server.py where Odoo clients are instantiated**

Pass the `timezone` from config when creating Odoo client instances. Find where `OdooV11Client` / `OdooV16Client` are constructed and pass `timezone=config.get("timezone", "Europe/Madrid")`.

- [ ] **Step 6: Run all Odoo tests**

Run: `cd daemon && python -m pytest tests/test_odoo_v11.py tests/test_odoo_v16.py -v`
Expected: All PASS

---

### Task 3: X11 capture diagnostics

**Files:**
- Modify: `daemon/mimir_daemon/platform/linux.py:137`

- [ ] **Step 1: Change xdotool log level and add startup diagnostic**

In `daemon/mimir_daemon/platform/linux.py`, at line 137, change:
```python
logger.warning("xdotool no encontrado. Instalar con: sudo apt install xdotool")
```
to:
```python
logger.error("xdotool no encontrado. Instalar con: sudo apt install xdotool")
```

Also in the `__init__` or setup method, add a startup diagnostic after backend detection (around line 42):

```python
if self._backend == "x11":
    # Verificar xdotool al arrancar
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow"],
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0:
            logger.info("xdotool verificado correctamente (ventana activa: %s)", result.stdout.strip())
        else:
            logger.error("xdotool fallo al arrancar: %s", result.stderr.strip())
    except FileNotFoundError:
        logger.error("xdotool no esta instalado. La captura X11 NO funcionara.")
    except Exception as e:
        logger.error("Error verificando xdotool: %s", e)
```

- [ ] **Step 2: Run platform tests**

Run: `cd daemon && python -m pytest tests/test_platform_linux.py -v`
Expected: All PASS

---

## Chunk 2: Sprint 2 — Issues Features (Backend)

### Task 4: Add issue_preferences table to SQLite

**Files:**
- Modify: `daemon/mimir_daemon/db.py`
- Test: `daemon/tests/test_server.py`

- [ ] **Step 1: Write failing test**

In `daemon/tests/test_server.py`, add:

```python
@pytest.mark.asyncio
async def test_issue_preferences_crud(db):
    """CRUD de preferencias de issues."""
    # Create
    await db.upsert_issue_preference(12345, manual_score=25, followed=True)
    # Read
    prefs = await db.get_all_issue_preferences()
    assert len(prefs) == 1
    assert prefs[0]["issue_id"] == 12345
    assert prefs[0]["manual_score"] == 25
    assert prefs[0]["followed"] == 1
    # Update
    await db.upsert_issue_preference(12345, manual_score=50)
    prefs = await db.get_all_issue_preferences()
    assert prefs[0]["manual_score"] == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd daemon && python -m pytest tests/test_server.py::test_issue_preferences_crud -v`
Expected: FAIL (method not found)

- [ ] **Step 3: Add table creation in db.py**

In `daemon/mimir_daemon/db.py`, in the `_init_db()` method, add after existing CREATE TABLE statements:

```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS issue_preferences (
        issue_id INTEGER PRIMARY KEY,
        manual_score INTEGER DEFAULT 0,
        followed BOOLEAN DEFAULT FALSE,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
""")
```

- [ ] **Step 4: Add CRUD methods in db.py**

```python
async def upsert_issue_preference(
    self, issue_id: int, manual_score: int | None = None, followed: bool | None = None
) -> None:
    """Crea o actualiza preferencia de issue."""
    async with self._lock:
        existing = await self._db.execute_fetchall(
            "SELECT * FROM issue_preferences WHERE issue_id = ?", (issue_id,)
        )
        if existing:
            updates = []
            params = []
            if manual_score is not None:
                updates.append("manual_score = ?")
                params.append(manual_score)
            if followed is not None:
                updates.append("followed = ?")
                params.append(followed)
            if updates:
                updates.append("updated_at = datetime('now')")
                params.append(issue_id)
                await self._db.execute(
                    f"UPDATE issue_preferences SET {', '.join(updates)} WHERE issue_id = ?",
                    params,
                )
        else:
            await self._db.execute(
                "INSERT INTO issue_preferences (issue_id, manual_score, followed) VALUES (?, ?, ?)",
                (issue_id, manual_score or 0, followed or False),
            )
        await self._db.commit()

async def get_all_issue_preferences(self) -> list[dict]:
    """Obtiene todas las preferencias de issues."""
    rows = await self._db.execute_fetchall("SELECT * FROM issue_preferences")
    return [dict(r) for r in rows]

async def get_followed_issue_ids(self) -> list[int]:
    """Obtiene IDs de issues seguidas."""
    rows = await self._db.execute_fetchall(
        "SELECT issue_id FROM issue_preferences WHERE followed = 1"
    )
    return [r["issue_id"] for r in rows]
```

- [ ] **Step 5: Run test**

Run: `cd daemon && python -m pytest tests/test_server.py::test_issue_preferences_crud -v`
Expected: PASS

---

### Task 5: Add GitLab source methods (search, notes, labels)

**Files:**
- Modify: `daemon/mimir_daemon/sources/gitlab.py`
- Test: `daemon/tests/test_gitlab_source.py`

- [ ] **Step 1: Write failing tests**

In `daemon/tests/test_gitlab_source.py`, add:

```python
@pytest.mark.asyncio
async def test_search_issues(gitlab_source, mock_response):
    """Busqueda de issues en todos los proyectos."""
    mock_response([{
        "id": 999, "iid": 1, "title": "Test issue",
        "state": "opened", "web_url": "https://...",
        "references": {"full": "group/project#1"},
        "labels": [], "assignees": [], "milestone": None,
        "due_date": None, "user_notes_count": 0,
    }])
    results = await gitlab_source.search_issues("Test")
    assert len(results) == 1
    assert results[0]["id"] == 999

@pytest.mark.asyncio
async def test_get_issue_notes(gitlab_source, mock_response):
    """Notas de una issue filtradas (solo user notes)."""
    mock_response([
        {"id": 1, "body": "User comment", "system": False, "author": {"username": "john"}, "created_at": "2026-03-17T10:00:00Z"},
        {"id": 2, "body": "added label", "system": True, "author": {"username": "john"}, "created_at": "2026-03-17T10:01:00Z"},
    ])
    notes = await gitlab_source.get_issue_notes("group%2Fproject", 1, per_page=5)
    assert len(notes) == 1
    assert notes[0]["body"] == "User comment"

@pytest.mark.asyncio
async def test_get_labels(gitlab_source, mock_response):
    """Labels unicas de todos los proyectos."""
    mock_response([
        {"name": "priority::critical", "color": "#ff0000"},
        {"name": "priority::high", "color": "#ff6600"},
    ])
    labels = await gitlab_source.get_labels(["group/project"])
    assert len(labels) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd daemon && python -m pytest tests/test_gitlab_source.py -k "search or notes or labels" -v`
Expected: FAIL

- [ ] **Step 3: Implement methods in gitlab.py**

In `daemon/mimir_daemon/sources/gitlab.py`, add to `GitLabSource` class:

```python
async def search_issues(self, query: str, per_page: int = 20) -> list[dict]:
    """Busca issues en todos los proyectos accesibles."""
    try:
        resp = await self._client.get(
            f"{self._url}/api/v4/issues",
            params={"search": query, "scope": "all", "state": "opened", "per_page": per_page},
            headers=self._headers,
        )
        resp.raise_for_status()
        issues = resp.json()
        for issue in issues:
            ref = issue.get("references", {}).get("full", "")
            issue["project_path"] = ref.rsplit("#", 1)[0] if "#" in ref else ""
        return issues
    except Exception as e:
        logger.error("Error buscando issues en GitLab: %s", e)
        return []

async def get_issue_notes(
    self, project_id: str, issue_iid: int, per_page: int = 5
) -> list[dict]:
    """Obtiene notas de usuario de una issue (excluye system notes)."""
    try:
        resp = await self._client.get(
            f"{self._url}/api/v4/projects/{project_id}/issues/{issue_iid}/notes",
            params={"sort": "desc", "per_page": per_page * 2},  # fetch extra to filter
            headers=self._headers,
        )
        resp.raise_for_status()
        notes = [n for n in resp.json() if not n.get("system", False)]
        return notes[:per_page]
    except Exception as e:
        logger.error("Error obteniendo notas de issue %s#%d: %s", project_id, issue_iid, e)
        return []

async def get_issues_by_ids(self, issue_ids: list[int]) -> list[dict]:
    """Obtiene issues por sus IDs globales."""
    if not issue_ids:
        return []
    try:
        # GitLab API acepta iids[] solo dentro de un proyecto,
        # pero /issues?iids[]=X funciona a nivel global con scope=all
        params = {"scope": "all", "state": "opened"}
        for iid in issue_ids:
            params.setdefault("iids[]", [])
        # Alternativa: buscar una por una por ID
        results = []
        for gid in issue_ids:
            try:
                resp = await self._client.get(
                    f"{self._url}/api/v4/issues/{gid}",
                    headers=self._headers,
                )
                if resp.status_code == 200:
                    issue = resp.json()
                    ref = issue.get("references", {}).get("full", "")
                    issue["project_path"] = ref.rsplit("#", 1)[0] if "#" in ref else ""
                    results.append(issue)
            except Exception:
                continue
        return results
    except Exception as e:
        logger.error("Error obteniendo issues por IDs: %s", e)
        return []

async def get_labels(self, project_paths: list[str] | None = None) -> list[dict]:
    """Obtiene labels unicas de los proyectos del usuario."""
    try:
        seen = set()
        labels = []
        # Si no se pasan proyectos, obtener de los issues actuales
        if not project_paths:
            issues = await self.get_issues()
            project_paths = list({i["project_path"] for i in issues})

        for path in project_paths:
            encoded = path.replace("/", "%2F")
            try:
                resp = await self._client.get(
                    f"{self._url}/api/v4/projects/{encoded}/labels",
                    params={"per_page": 100},
                    headers=self._headers,
                )
                if resp.status_code == 200:
                    for label in resp.json():
                        name = label["name"]
                        if name not in seen:
                            seen.add(name)
                            labels.append({"name": name, "color": label.get("color", "")})
            except Exception:
                continue
        return sorted(labels, key=lambda l: l["name"])
    except Exception as e:
        logger.error("Error obteniendo labels de GitLab: %s", e)
        return []
```

- [ ] **Step 4: Run tests**

Run: `cd daemon && python -m pytest tests/test_gitlab_source.py -v`
Expected: All PASS

---

### Task 6: Add FastAPI endpoints for issues features

**Files:**
- Modify: `daemon/mimir_daemon/server.py` (after line 705)

- [ ] **Step 1: Add issue preferences endpoints**

In `daemon/mimir_daemon/server.py`, after the existing GitLab endpoints (around line 705), add:

```python
@app.get("/gitlab/issues/preferences")
async def get_issue_preferences() -> list[dict]:
    """Obtiene todas las preferencias de issues."""
    return await db.get_all_issue_preferences()

@app.put("/gitlab/issues/{issue_id}/preferences")
async def update_issue_preferences(issue_id: int, body: dict = Body(...)) -> dict:
    """Actualiza preferencias de una issue."""
    await db.upsert_issue_preference(
        issue_id,
        manual_score=body.get("manual_score"),
        followed=body.get("followed"),
    )
    return {"ok": True}

@app.get("/gitlab/issues/followed")
async def get_followed_issues() -> list[dict]:
    """Obtiene issues seguidas con datos frescos de GitLab."""
    ids = await db.get_followed_issue_ids()
    if not ids:
        return []
    gitlab = _source_registry.get("gitlab")
    if not gitlab:
        raise HTTPException(404, "GitLab no configurado")
    return await gitlab.get_issues_by_ids(ids)

@app.get("/gitlab/issues/search")
async def search_gitlab_issues(q: str = Query(..., min_length=2)) -> list[dict]:
    """Busca issues en GitLab."""
    gitlab = _source_registry.get("gitlab")
    if not gitlab:
        raise HTTPException(404, "GitLab no configurado")
    return await gitlab.search_issues(q, per_page=20)

@app.get("/gitlab/labels")
async def get_gitlab_labels() -> list[dict]:
    """Obtiene labels unicas de los proyectos del usuario."""
    gitlab = _source_registry.get("gitlab")
    if not gitlab:
        raise HTTPException(404, "GitLab no configurado")
    return await gitlab.get_labels()

@app.get("/gitlab/issues/{project_id}/{issue_iid}/notes")
async def get_issue_notes(project_id: str, issue_iid: int, per_page: int = Query(default=5)) -> list[dict]:
    """Obtiene notas de usuario de una issue."""
    gitlab = _source_registry.get("gitlab")
    if not gitlab:
        raise HTTPException(404, "GitLab no configurado")
    return await gitlab.get_issue_notes(project_id, issue_iid, per_page)
```

- [ ] **Step 2: Add task_id filter to GET /odoo/entries**

Modify the existing `get_timesheet_entries()` endpoint to accept optional `task_id`:

```python
@app.get("/odoo/entries")
async def get_timesheet_entries(
    date_from: str = Query(alias="from"),
    date_to: str = Query(alias="to"),
    task_id: int | None = Query(default=None),
) -> list[dict]:
```

When `task_id` is provided, filter the results by task_id after fetching from Odoo.

- [ ] **Step 3: Add PUT /odoo/entries/{entry_id}**

```python
@app.put("/odoo/entries/{entry_id}")
async def update_timesheet_entry(entry_id: int, body: dict = Body(...)) -> dict:
    """Actualiza una entrada de timesheet en Odoo."""
    if not _odoo_client:
        raise HTTPException(400, "Odoo no configurado")
    entry = TimesheetEntryData(
        date=body.get("date", ""),
        project_id=body["project_id"],
        task_id=body.get("task_id"),
        description=body.get("description", ""),
        hours=body["hours"],
    )
    try:
        await _odoo_client.update_entry(entry_id, entry)
        return {"ok": True}
    except Exception as e:
        raise HTTPException(400, f"Error actualizando en Odoo: {e}")
```

- [ ] **Step 4: Run server tests**

Run: `cd daemon && python -m pytest tests/test_server.py -v`
Expected: All PASS

---

### Task 7: Sync Rust AppConfig + add Tauri commands

**Files:**
- Modify: `src-tauri/src/commands/config.rs`
- Modify: `src-tauri/src/commands/daemon.rs`
- Modify: `src-tauri/src/lib.rs`

- [ ] **Step 1: Add missing fields to Rust AppConfig**

In `src-tauri/src/commands/config.rs`, add to the struct (after line 29):

```rust
pub timezone: String,
pub signals_retention_days: u32,
pub blocks_retention_days: u32,
pub google_client_id: String,
pub google_client_secret: String,
pub capture_window: bool,
pub capture_git: bool,
pub capture_idle: bool,
pub capture_audio: bool,
pub capture_ssh: bool,
pub gitlab_priority_labels: Vec<PriorityLabelMapping>,
pub issue_notes_count: u32,
```

Add the struct before `AppConfig`:
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PriorityLabelMapping {
    pub label: String,
    pub weight: u32,
}
```

Add defaults in `impl Default`:
```rust
timezone: "Europe/Madrid".to_string(),
signals_retention_days: 90,
blocks_retention_days: 180,
google_client_id: String::new(),
google_client_secret: String::new(),
capture_window: true,
capture_git: true,
capture_idle: true,
capture_audio: true,
capture_ssh: true,
gitlab_priority_labels: vec![
    PriorityLabelMapping { label: "priority::critical".to_string(), weight: 100 },
    PriorityLabelMapping { label: "priority::high".to_string(), weight: 75 },
    PriorityLabelMapping { label: "priority::medium".to_string(), weight: 50 },
    PriorityLabelMapping { label: "priority::low".to_string(), weight: 25 },
    PriorityLabelMapping { label: "Expedite".to_string(), weight: 100 },
],
issue_notes_count: 5,
```

- [ ] **Step 2: Add Tauri commands in daemon.rs**

In `src-tauri/src/commands/daemon.rs`, add:

```rust
#[tauri::command]
pub async fn get_issue_preferences() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/issues/preferences").await
}

#[tauri::command]
pub async fn update_issue_preferences(issue_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put(&format!("/gitlab/issues/{}/preferences", issue_id), &body).await
}

#[tauri::command]
pub async fn search_gitlab_issues(q: String) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/search?q={}", q)).await
}

#[tauri::command]
pub async fn get_followed_issues() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/issues/followed").await
}

#[tauri::command]
pub async fn get_gitlab_labels() -> Result<serde_json::Value, String> {
    get_client().get("/gitlab/labels").await
}

#[tauri::command]
pub async fn get_issue_notes(project_id: String, issue_iid: u64, per_page: u32) -> Result<serde_json::Value, String> {
    get_client().get(&format!("/gitlab/issues/{}/{}/notes?per_page={}", project_id, issue_iid, per_page)).await
}

#[tauri::command]
pub async fn update_timesheet_entry(entry_id: u64, body: serde_json::Value) -> Result<serde_json::Value, String> {
    get_client().put(&format!("/odoo/entries/{}", entry_id), &body).await
}
```

- [ ] **Step 3: Register commands in lib.rs**

In `src-tauri/src/lib.rs`, add to the `generate_handler!` macro invocation:

```rust
daemon::get_issue_preferences,
daemon::update_issue_preferences,
daemon::search_gitlab_issues,
daemon::get_followed_issues,
daemon::get_gitlab_labels,
daemon::get_issue_notes,
daemon::update_timesheet_entry,
```

- [ ] **Step 4: Verify Rust compiles**

Run: `cd src-tauri && cargo check`
Expected: No errors

---

### Task 8: Add API methods in frontend

**Files:**
- Modify: `src/lib/api.ts`
- Modify: `src/lib/types.ts`

- [ ] **Step 1: Add types**

In `src/lib/types.ts`, add after `AppConfig` (after line 179):

```typescript
export interface IssuePreference {
  issue_id: number;
  manual_score: number;
  followed: boolean;
}

export interface GitLabLabel {
  name: string;
  color: string;
}

export interface GitLabNote {
  id: number;
  body: string;
  author: { username: string };
  created_at: string;
}
```

Add to `AppConfig` (before closing brace):
```typescript
  gitlab_priority_labels: Array<{ label: string; weight: number }>;
  issue_notes_count: number;
```

- [ ] **Step 2: Add API methods**

In `src/lib/api.ts`, add before the closing of the api object:

```typescript
async getIssuePreferences(): Promise<IssuePreference[]> {
  if (await isTauri()) return tauriInvoke('get_issue_preferences');
  return httpGet('/gitlab/issues/preferences');
},

async updateIssuePreferences(issueId: number, body: Partial<IssuePreference>): Promise<void> {
  if (await isTauri()) return tauriInvoke('update_issue_preferences', { issueId, body });
  return httpPut(`/gitlab/issues/${issueId}/preferences`, body);
},

async searchGitlabIssues(q: string): Promise<GitLabIssue[]> {
  if (await isTauri()) return tauriInvoke('search_gitlab_issues', { q });
  return httpGet(`/gitlab/issues/search?q=${encodeURIComponent(q)}`);
},

async getFollowedIssues(): Promise<GitLabIssue[]> {
  if (await isTauri()) return tauriInvoke('get_followed_issues');
  return httpGet('/gitlab/issues/followed');
},

async getGitlabLabels(): Promise<GitLabLabel[]> {
  if (await isTauri()) return tauriInvoke('get_gitlab_labels');
  return httpGet('/gitlab/labels');
},

async getIssueNotes(projectId: string, issueIid: number, perPage: number = 5): Promise<GitLabNote[]> {
  if (await isTauri()) return tauriInvoke('get_issue_notes', { projectId, issueIid, perPage });
  return httpGet(`/gitlab/issues/${projectId}/${issueIid}/notes?per_page=${perPage}`);
},

async updateTimesheetEntry(entryId: number, body: { description?: string; hours?: number; project_id?: number; task_id?: number }): Promise<void> {
  if (await isTauri()) return tauriInvoke('update_timesheet_entry', { entryId, body });
  return httpPut(`/odoo/entries/${entryId}`, body);
},
```

- [ ] **Step 3: Verify TypeScript**

Run: `npx vue-tsc --noEmit`
Expected: No errors

---

## Chunk 3: Sprint 2 — Issues Features (Frontend)

### Task 9: Update scoring.ts to use dynamic labels

**Files:**
- Modify: `src/lib/scoring.ts`

- [ ] **Step 1: Make PRIORITY_LABELS dynamic**

Replace the hardcoded `PRIORITY_LABELS` constant (lines 20-26) with a function:

```typescript
let dynamicPriorityLabels: Record<string, number> = {
  'priority::critical': 100,
  'priority::high': 75,
  'priority::medium': 50,
  'priority::low': 25,
  'Expedite': 100,
};

export function setPriorityLabels(labels: Array<{ label: string; weight: number }>) {
  dynamicPriorityLabels = {};
  for (const { label, weight } of labels) {
    dynamicPriorityLabels[label] = weight;
  }
}
```

Update `scoreLabelPriority()` (line 28-35) to use `dynamicPriorityLabels` instead of `PRIORITY_LABELS`.

- [ ] **Step 2: Initialize from config in issues store**

In `src/stores/issues.ts`, call `setPriorityLabels(configStore.config.gitlab_priority_labels)` when loading issues.

---

### Task 10: Update issues store with preferences + followed + search

**Files:**
- Modify: `src/stores/issues.ts`

- [ ] **Step 1: Extend store**

Rewrite the store to include:

```typescript
// New state
const preferences = ref<Map<number, IssuePreference>>(new Map());
const followedIssues = ref<GitLabIssue[]>([]);
const searchResults = ref<GitLabIssue[]>([]);
const searchLoading = ref(false);
const activeFilter = ref<'all' | 'assigned' | 'followed'>('all');

// Merge preferences into issues
const allIssues = computed(() => {
  const assigned = issues.value;
  const followed = followedIssues.value.filter(
    fi => !assigned.some(ai => ai.id === fi.id)
  );
  return [...assigned, ...followed];
});

const scoredIssues = computed(() => {
  return allIssues.value
    .map(issue => {
      const pref = preferences.value.get(issue.id);
      return {
        ...issue,
        manual_priority: pref?.manual_score ?? issue.manual_priority ?? 0,
        _followed: pref?.followed ?? false,
      };
    })
    .map(issue => ({ ...issue, score: computeIssueScore(issue) }))
    .sort((a, b) => b.score - a.score);
});

const filteredIssues = computed(() => {
  let result = scoredIssues.value;
  if (activeFilter.value === 'assigned') {
    result = result.filter(i => !i._followed);
  } else if (activeFilter.value === 'followed') {
    result = result.filter(i => i._followed);
  }
  // Apply text filter
  if (filterText.value) {
    const q = filterText.value.toLowerCase();
    result = result.filter(i =>
      i.title.toLowerCase().includes(q) ||
      i.project_path.toLowerCase().includes(q) ||
      i.labels.some(l => l.toLowerCase().includes(q))
    );
  }
  return result;
});

// New actions
async function fetchPreferences() {
  const prefs = await api.getIssuePreferences();
  preferences.value = new Map(prefs.map(p => [p.issue_id, p]));
}

async function fetchFollowedIssues() {
  const followed = await api.getFollowedIssues();
  followedIssues.value = followed;
}

async function searchIssues(query: string) {
  if (query.length < 2) { searchResults.value = []; return; }
  searchLoading.value = true;
  try {
    searchResults.value = await api.searchGitlabIssues(query);
  } finally {
    searchLoading.value = false;
  }
}

async function updatePreference(issueId: number, data: Partial<IssuePreference>) {
  await api.updateIssuePreferences(issueId, data);
  // Update local
  const existing = preferences.value.get(issueId) || { issue_id: issueId, manual_score: 0, followed: false };
  preferences.value.set(issueId, { ...existing, ...data });
}

async function followIssue(issueId: number) {
  await updatePreference(issueId, { followed: true });
  await fetchFollowedIssues();
}

async function unfollowIssue(issueId: number) {
  await updatePreference(issueId, { followed: false });
  followedIssues.value = followedIssues.value.filter(i => i.id !== issueId);
}
```

Update `fetchIssues()` to also call `fetchPreferences()` and `fetchFollowedIssues()`.

---

### Task 11: Create IssueDetailModal component

**Files:**
- Create: `src/components/issues/IssueDetailModal.vue`

- [ ] **Step 1: Install markdown dependencies**

Run: `npm install marked dompurify && npm install -D @types/dompurify`

- [ ] **Step 2: Create component**

```vue
<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import ModalDialog from '@/components/shared/ModalDialog.vue';
import ScoreBadge from '@/components/shared/ScoreBadge.vue';
import { useFormatting } from '@/composables/useFormatting';
import { useConfigStore } from '@/stores/config';
import { useIssuesStore } from '@/stores/issues';
import api from '@/lib/api';
import type { GitLabIssue, GitLabNote } from '@/lib/types';

const props = defineProps<{ issue: GitLabIssue | null; open: boolean }>();
const emit = defineEmits<{ close: [] }>();

const { formatHours } = useFormatting();
const configStore = useConfigStore();
const issuesStore = useIssuesStore();

const notes = ref<GitLabNote[]>([]);
const totalHours = ref(0);
const loadingNotes = ref(false);
const editingScore = ref(false);
const manualScore = ref(0);

const descriptionHtml = computed(() => {
  if (!props.issue?.description) return '';
  return DOMPurify.sanitize(marked.parse(props.issue.description) as string);
});

watch(() => props.issue, async (issue) => {
  if (!issue) return;
  notes.value = [];
  totalHours.value = 0;
  loadingNotes.value = true;

  // Cargar notas
  const projectId = encodeURIComponent(issue.project_path);
  const perPage = configStore.config.issue_notes_count || 5;
  try {
    notes.value = await api.getIssueNotes(projectId, issue.iid, perPage);
  } catch { /* ignore */ }

  // Cargar tiempo dedicado desde Odoo
  if (issue.iid) {
    try {
      const entries = await api.getTimesheetEntries('2020-01-01', '2099-12-31', issue.iid);
      totalHours.value = entries.reduce((sum: number, e: any) => sum + (e.unit_amount || e.hours || 0), 0);
    } catch { /* ignore */ }
  }

  // Score manual
  const pref = issuesStore.preferences.get(issue.id);
  manualScore.value = pref?.manual_score ?? 0;

  loadingNotes.value = false;
}, { immediate: true });

async function saveScore() {
  if (!props.issue) return;
  await issuesStore.updatePreference(props.issue.id, { manual_score: manualScore.value });
  editingScore.value = false;
}

function openGitLab() {
  if (props.issue) window.open(props.issue.web_url, '_blank');
}
</script>

<template>
  <ModalDialog :open="open" :title="`${issue?.project_path}#${issue?.iid}`" @close="emit('close')">
    <div v-if="issue" class="issue-detail">
      <h3 class="issue-title">{{ issue.title }}</h3>

      <div class="issue-labels">
        <span v-for="label in issue.labels" :key="label" class="label-tag">{{ label }}</span>
      </div>

      <div class="issue-meta">
        <div v-if="issue.milestone"><strong>Milestone:</strong> {{ issue.milestone }}</div>
        <div v-if="issue.due_date"><strong>Fecha limite:</strong> {{ issue.due_date }}</div>
        <div v-if="issue.assignees?.length">
          <strong>Asignados:</strong> {{ issue.assignees.map(a => a.username).join(', ') }}
        </div>
      </div>

      <div class="issue-scores">
        <div><strong>Score total:</strong> <ScoreBadge :score="issue.score" /></div>
        <div class="manual-score">
          <strong>Score manual:</strong>
          <template v-if="editingScore">
            <input v-model.number="manualScore" type="number" min="0" max="100" class="score-input" />
            <button class="btn btn-sm btn-success" @click="saveScore">OK</button>
            <button class="btn btn-sm" @click="editingScore = false">X</button>
          </template>
          <template v-else>
            <span class="score-value" @click="editingScore = true">{{ manualScore || '—' }}</span>
          </template>
        </div>
      </div>

      <div v-if="totalHours > 0" class="issue-time">
        <strong>Tiempo dedicado (Odoo):</strong> {{ formatHours(totalHours) }}
      </div>

      <div v-if="issue.description" class="issue-description">
        <strong>Descripcion</strong>
        <div class="markdown-body" v-html="descriptionHtml"></div>
      </div>

      <div class="issue-notes">
        <strong>Ultimos comentarios</strong>
        <div v-if="loadingNotes" class="loading">Cargando...</div>
        <div v-else-if="notes.length === 0" class="empty">Sin comentarios</div>
        <div v-else class="notes-list">
          <div v-for="note in notes" :key="note.id" class="note">
            <div class="note-header">
              <span class="note-author">{{ note.author.username }}</span>
              <span class="note-date">{{ note.created_at }}</span>
            </div>
            <div class="note-body">{{ note.body }}</div>
          </div>
        </div>
      </div>

      <div class="issue-actions">
        <button class="btn btn-primary" @click="openGitLab">Ir a GitLab</button>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.issue-detail { display: flex; flex-direction: column; gap: 1rem; }
.issue-title { margin: 0; font-size: 1.1rem; }
.issue-labels { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.issue-meta { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.9rem; }
.issue-scores { display: flex; gap: 1rem; align-items: center; }
.manual-score { display: flex; align-items: center; gap: 0.5rem; }
.score-input { width: 60px; }
.score-value { cursor: pointer; text-decoration: underline dotted; }
.issue-description { max-height: 200px; overflow-y: auto; }
.markdown-body { font-size: 0.9rem; line-height: 1.5; }
.notes-list { display: flex; flex-direction: column; gap: 0.5rem; }
.note { border-left: 2px solid var(--border); padding-left: 0.5rem; }
.note-header { font-size: 0.8rem; color: var(--text-muted); }
.note-author { font-weight: bold; margin-right: 0.5rem; }
.issue-actions { display: flex; justify-content: flex-end; padding-top: 0.5rem; }
</style>
```

---

### Task 12: Update IssuesView with search bar, filter, and click handler

**Files:**
- Modify: `src/views/IssuesView.vue`
- Modify: `src/components/issues/IssueTable.vue`

- [ ] **Step 1: Add search bar and filter to IssuesView**

Add to IssuesView template: search input with dropdown, filter tabs (Todas/Asignadas/Seguidas), and IssueDetailModal.

```vue
<!-- Add state in setup -->
const searchQuery = ref('');
const selectedIssue = ref<GitLabIssue | null>(null);
const showDetail = ref(false);
let searchTimeout: ReturnType<typeof setTimeout>;

function onSearch(q: string) {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => issuesStore.searchIssues(q), 300);
}

function openIssueDetail(issue: GitLabIssue) {
  selectedIssue.value = issue;
  showDetail.value = true;
}
```

Add to template:
- Search input above the filter bar
- Search results dropdown (absolute positioned)
- Filter tabs: Todas | Asignadas | Seguidas
- `<IssueDetailModal :issue="selectedIssue" :open="showDetail" @close="showDetail = false" />`

- [ ] **Step 2: Add click handler to IssueTable**

In `src/components/issues/IssueTable.vue`, add emit for row click:

```typescript
const emit = defineEmits<{ 'select': [issue: GitLabIssue] }>();
```

On the `<tr>` in the loop:
```html
<tr v-for="issue in sorted" :key="issue.id" class="clickable-row" @click="emit('select', issue)">
```

Keep the title link for right-click → direct GitLab navigation.

- [ ] **Step 3: Verify**

Run: `npx vue-tsc --noEmit`
Expected: No errors

---

### Task 13: Add priority labels config to GitLab settings tab

**Files:**
- Modify: `src/views/SettingsView.vue`

- [ ] **Step 1: Add priority mapping section**

In the GitLab tab section of SettingsView.vue, add after the existing GitLab config fields:

```vue
<div class="setting-group">
  <h4>Mapeo de prioridad de labels</h4>
  <p class="help-text">Configura que labels de GitLab determinan la prioridad de las issues.</p>
  <table class="priority-table">
    <thead>
      <tr><th>Label</th><th>Peso (0-100)</th><th></th></tr>
    </thead>
    <tbody>
      <tr v-for="(mapping, idx) in localConfig.gitlab_priority_labels" :key="idx">
        <td><input v-model="mapping.label" placeholder="ej: priority::critical" /></td>
        <td><input v-model.number="mapping.weight" type="number" min="0" max="100" /></td>
        <td><button class="btn btn-sm btn-danger" @click="localConfig.gitlab_priority_labels.splice(idx, 1)">X</button></td>
      </tr>
    </tbody>
  </table>
  <button class="btn btn-sm" @click="localConfig.gitlab_priority_labels.push({ label: '', weight: 50 })">
    + Anadir regla
  </button>
</div>
```

- [ ] **Step 2: Verify**

Run: `npx vue-tsc --noEmit`
Expected: No errors

---

## Chunk 4: Sprint 3 — Timesheet Edit Popup

### Task 14: Create TimesheetEditModal component

**Files:**
- Create: `src/components/timesheets/TimesheetEditModal.vue`

- [ ] **Step 1: Create component**

```vue
<script setup lang="ts">
import { ref, watch } from 'vue';
import ModalDialog from '@/components/shared/ModalDialog.vue';
import CustomSelect from '@/components/shared/CustomSelect.vue';
import { useOdooProjects } from '@/composables/useOdooProjects';
import { useConfigStore } from '@/stores/config';
import api from '@/lib/api';

interface TimesheetEntry {
  id: number;
  date: string;
  project_id: number;
  project_name: string;
  task_id: number | null;
  task_name: string;
  description: string;
  unit_amount: number;
}

const props = defineProps<{ entry: TimesheetEntry | null; open: boolean }>();
const emit = defineEmits<{ close: []; saved: [] }>();

const configStore = useConfigStore();
const { projects, tasks, loadProjects, loadTasks } = useOdooProjects();

const editDescription = ref('');
const editHours = ref(0);
const editProjectId = ref<number | null>(null);
const editTaskId = ref<number | null>(null);
const saving = ref(false);
const error = ref('');

watch(() => props.entry, (entry) => {
  if (!entry) return;
  editDescription.value = entry.description;
  editHours.value = entry.unit_amount;
  editProjectId.value = entry.project_id;
  editTaskId.value = entry.task_id;
  loadProjects();
  if (entry.project_id) loadTasks(entry.project_id);
}, { immediate: true });

watch(editProjectId, (pid) => {
  if (pid) loadTasks(pid);
  editTaskId.value = null;
});

async function save() {
  if (!props.entry) return;
  saving.value = true;
  error.value = '';
  try {
    await api.updateTimesheetEntry(props.entry.id, {
      description: editDescription.value,
      hours: editHours.value,
      project_id: editProjectId.value!,
      task_id: editTaskId.value ?? undefined,
    });
    emit('saved');
    emit('close');
  } catch (e: any) {
    error.value = e.message || 'Error al guardar';
  } finally {
    saving.value = false;
  }
}

function openInOdoo() {
  if (!props.entry) return;
  const url = `${configStore.config.odoo_url}/web#id=${props.entry.id}&model=account.analytic.line&view_type=form`;
  window.open(url, '_blank');
}
</script>

<template>
  <ModalDialog :open="open" title="Editar parte de horas" @close="emit('close')">
    <div v-if="entry" class="ts-edit">
      <div class="field">
        <label>Fecha</label>
        <span class="readonly">{{ entry.date }}</span>
      </div>
      <div class="field">
        <label>Proyecto</label>
        <CustomSelect
          :model-value="editProjectId"
          :options="projects.map(p => ({ value: p.id, label: p.name }))"
          @update:model-value="editProjectId = $event"
        />
      </div>
      <div class="field">
        <label>Tarea</label>
        <CustomSelect
          :model-value="editTaskId"
          :options="tasks.map(t => ({ value: t.id, label: t.name }))"
          @update:model-value="editTaskId = $event"
        />
      </div>
      <div class="field">
        <label>Descripcion</label>
        <textarea v-model="editDescription" rows="3"></textarea>
      </div>
      <div class="field">
        <label>Horas</label>
        <input v-model.number="editHours" type="number" min="0" step="0.25" />
      </div>
      <div v-if="error" class="error">{{ error }}</div>
      <div class="actions">
        <button class="btn" @click="openInOdoo">Ir a Odoo</button>
        <button class="btn btn-primary" :disabled="saving" @click="save">
          {{ saving ? 'Guardando...' : 'Guardar' }}
        </button>
      </div>
    </div>
  </ModalDialog>
</template>

<style scoped>
.ts-edit { display: flex; flex-direction: column; gap: 0.75rem; }
.field { display: flex; flex-direction: column; gap: 0.25rem; }
.field label { font-weight: bold; font-size: 0.85rem; }
.readonly { color: var(--text-muted); }
.actions { display: flex; justify-content: flex-end; gap: 0.5rem; padding-top: 0.5rem; }
.error { color: var(--error); font-size: 0.85rem; }
textarea { resize: vertical; }
</style>
```

---

### Task 15: Wire TimesheetEditModal into TimesheetsView

**Files:**
- Modify: `src/views/TimesheetsView.vue`

- [ ] **Step 1: Add modal and click handler**

In `src/views/TimesheetsView.vue` setup:

```typescript
import TimesheetEditModal from '@/components/timesheets/TimesheetEditModal.vue';

const selectedEntry = ref(null);
const showEditModal = ref(false);

function openEntry(entry: any) {
  selectedEntry.value = entry;
  showEditModal.value = true;
}

function onSaved() {
  timesheetsStore.fetchEntries();
}
```

In template, add click handler to table rows:
```html
<tr v-for="entry in sortEntries(group.entries)" :key="entry.id" class="clickable-row" @click="openEntry(entry)">
```

Add modal at the end of the template:
```html
<TimesheetEditModal
  :entry="selectedEntry"
  :open="showEditModal"
  @close="showEditModal = false"
  @saved="onSaved"
/>
```

- [ ] **Step 2: Verify**

Run: `npx vue-tsc --noEmit`
Expected: No errors

---

## Chunk 5: Final verification

### Task 16: Run all tests

- [ ] **Step 1: Backend tests**

Run: `cd daemon && python -m pytest tests/ -v`
Expected: All PASS (existing + new)

- [ ] **Step 2: Frontend type check**

Run: `npx vue-tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Rust check**

Run: `cd src-tauri && cargo check`
Expected: No errors
