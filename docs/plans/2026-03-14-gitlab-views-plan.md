# Fase 5 — Vistas GitLab: Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Conectar la integración GitLab existente con el servidor y el frontend para mostrar issues y MRs con scoring y polling.

**Architecture:** GitLabSource (httpx async) → SourceRegistry → server.py endpoints. Frontend stores ya aplican scoring en TypeScript. Vistas añaden polling periódico mientras están activas.

**Tech Stack:** Python (httpx, FastAPI), Vue 3 + TypeScript (Pinia stores, composables).

---

### Task 1: Conectar GitLab con server.py + SourceRegistry

**Files:**
- Modify: `daemon/mimir_daemon/server.py`
- Modify: `daemon/mimir_daemon/main.py`
- Test: `daemon/tests/test_server.py`

**Step 1: Write failing tests**

Add to `daemon/tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_get_gitlab_issues_no_source(client):
    """GET /gitlab/issues devuelve lista vacia sin source configurado."""
    resp = await client.get("/gitlab/issues")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_gitlab_merge_requests_no_source(client):
    """GET /gitlab/merge_requests devuelve lista vacia sin source."""
    resp = await client.get("/gitlab/merge_requests")
    assert resp.status_code == 200
    assert resp.json() == []
```

**Step 2: Run tests to verify they pass (stubs already return [])**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_server.py::test_get_gitlab_issues_no_source tests/test_server.py::test_get_gitlab_merge_requests_no_source -v`
Expected: PASS (the stubs already return [])

**Step 3: Write tests for when source IS configured**

First, add `SourceRegistry` import and a mock GitLab source. Add at top of `daemon/tests/test_server.py` (among imports):

```python
from mimir_daemon.sources.registry import SourceRegistry
from mimir_daemon.sources.base import VCSSource
```

Add mock class after `MockPlatform`:

```python
class MockGitLabSource(VCSSource):
    """Source GitLab falso para tests."""

    async def get_issues(self):
        return [
            {
                "id": 1, "iid": 42, "title": "Fix login bug",
                "description": "Login fails on mobile",
                "state": "opened", "web_url": "https://gitlab.test/issues/42",
                "project_path": "team/backend",
                "labels": ["bug", "priority::high"],
                "assignees": [{"id": 1, "username": "dev1", "name": "Dev One", "avatar_url": ""}],
                "milestone": None, "due_date": None,
                "created_at": "2026-03-01T10:00:00Z",
                "updated_at": "2026-03-13T15:00:00Z",
                "user_notes_count": 3,
                "has_conflicts": False,
                "score": 0, "manual_priority": None,
            }
        ]

    async def get_merge_requests(self):
        return [
            {
                "id": 10, "iid": 7, "title": "feat: add auth module",
                "description": "Implements JWT auth",
                "state": "opened", "web_url": "https://gitlab.test/mr/7",
                "project_path": "team/backend",
                "labels": [],
                "assignees": [{"id": 1, "username": "dev1", "name": "Dev One", "avatar_url": ""}],
                "reviewers": [],
                "source_branch": "feat/auth", "target_branch": "main",
                "has_conflicts": False, "pipeline_status": "success",
                "created_at": "2026-03-10T10:00:00Z",
                "updated_at": "2026-03-13T12:00:00Z",
                "user_notes_count": 1,
                "score": 0, "manual_priority": None,
            }
        ]
```

Update the `app` fixture to include `SourceRegistry`:

```python
@pytest.fixture
def source_registry():
    reg = SourceRegistry()
    reg.register_vcs("gitlab", MockGitLabSource())
    return reg


@pytest.fixture
def app(db, registry, source_registry):
    from mimir_daemon.ai.service import AIService
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    ai_service = AIService(db=db, provider=None)
    return create_app(db=db, poller=poller, registry=registry, ai_service=ai_service,
                      source_registry=source_registry)
```

Add tests:

```python
@pytest.mark.asyncio
async def test_get_gitlab_issues_with_source(client):
    """GET /gitlab/issues devuelve issues del source configurado."""
    resp = await client.get("/gitlab/issues")
    assert resp.status_code == 200
    issues = resp.json()
    assert len(issues) == 1
    assert issues[0]["title"] == "Fix login bug"
    assert issues[0]["project_path"] == "team/backend"


@pytest.mark.asyncio
async def test_get_gitlab_merge_requests_with_source(client):
    """GET /gitlab/merge_requests devuelve MRs del source."""
    resp = await client.get("/gitlab/merge_requests")
    assert resp.status_code == 200
    mrs = resp.json()
    assert len(mrs) == 1
    assert mrs[0]["title"] == "feat: add auth module"
    assert mrs[0]["source_branch"] == "feat/auth"
```

**Step 4: Run tests to verify they fail**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_server.py::test_get_gitlab_issues_with_source -v`
Expected: FAIL (create_app doesn't accept source_registry yet)

**Step 5: Update server.py**

In `daemon/mimir_daemon/server.py`:

a) Add import at top:
```python
from .sources.registry import SourceRegistry
```

b) Update `create_app` signature to add `source_registry`:
```python
def create_app(
    db: Database,
    poller: Poller,
    registry: IntegrationRegistry | None = None,
    ai_service: "AIService | None" = None,
    source_registry: SourceRegistry | None = None,
    version: str = "0.1.0",
) -> FastAPI:
```

c) After `_registry = registry or IntegrationRegistry()`, add:
```python
    _source_registry = source_registry or SourceRegistry()
```

d) Replace the GitLab stubs:
```python
    # --- GitLab ---

    @app.get("/gitlab/issues")
    async def get_gitlab_issues() -> list:
        """Obtiene issues de GitLab."""
        try:
            return await _source_registry.get_all_issues()
        except Exception as e:
            logger.error("Error obteniendo issues de GitLab: %s", e)
            return []

    @app.get("/gitlab/merge_requests")
    async def get_gitlab_merge_requests() -> list:
        """Obtiene merge requests de GitLab."""
        try:
            return await _source_registry.get_all_merge_requests()
        except Exception as e:
            logger.error("Error obteniendo MRs de GitLab: %s", e)
            return []
```

**Step 6: Update main.py**

In `daemon/mimir_daemon/main.py`:

a) Add import:
```python
from .sources.registry import SourceRegistry
```

b) In `run_daemon`, after creating `registry` and before creating `poller`, add:
```python
    source_registry = SourceRegistry()
```

c) Update `create_app` call:
```python
    app = create_app(
        db=db, poller=poller, registry=registry,
        ai_service=ai_service, source_registry=source_registry, version=VERSION,
    )
```

**Step 7: Run tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_server.py -v`
Expected: ALL PASS

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add daemon/mimir_daemon/server.py daemon/mimir_daemon/main.py daemon/tests/test_server.py
git commit -m "feat: connect GitLab source to server endpoints"
```

---

### Task 2: Configurar GitLabSource via PUT /config

**Files:**
- Modify: `daemon/mimir_daemon/server.py` (update_config handler)
- Test: `daemon/tests/test_server.py`

**Step 1: Write failing test**

Add to `daemon/tests/test_server.py`:

```python
@pytest.mark.asyncio
async def test_put_config_gitlab(client):
    """PUT /config con gitlab_url y token configura el source."""
    resp = await client.put("/config", json={
        "odoo_url": "", "odoo_version": "v16", "odoo_db": "", "odoo_username": "",
        "odoo_token": "", "gitlab_url": "https://gitlab.example.com",
        "gitlab_token": "glpat-test-token",
        "ai_provider": "none", "ai_api_key": "",
        "ai_user_role": "technical", "ai_custom_context": "",
    })
    assert resp.status_code == 200

    # Verificar integration-status
    resp2 = await client.get("/config/integration-status")
    data = resp2.json()
    assert data["gitlab"]["configured"] is True
```

**Step 2: Run test to verify it fails**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_server.py::test_put_config_gitlab -v`
Expected: FAIL (no "gitlab" key in integration-status)

**Step 3: Update server.py**

a) In `update_config`, after the AI configuration block and before saving to preferences, add:

```python
        # Configurar GitLab source
        if req.gitlab_url and req.gitlab_token:
            try:
                from .sources.gitlab import GitLabSource
                gitlab_source = GitLabSource(url=req.gitlab_url, token=req.gitlab_token)
                _source_registry.register_vcs("gitlab", gitlab_source)
                logger.info("GitLab source configurado: %s", req.gitlab_url)
            except Exception as e:
                logger.error("Error configurando GitLab: %s", e)
```

b) Update `get_integration_status` to include GitLab:

```python
    @app.get("/config/integration-status")
    async def get_integration_status() -> dict:
        """Devuelve el estado de las integraciones configuradas."""
        gitlab_sources = _source_registry._vcs_sources
        return {
            "odoo": {
                "configured": _registry.timesheet is not None,
                "client_type": type(_registry.timesheet).__name__ if _registry.timesheet else None,
            },
            "gitlab": {
                "configured": "gitlab" in gitlab_sources,
            },
        }
```

**Step 4: Run tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add daemon/mimir_daemon/server.py daemon/tests/test_server.py
git commit -m "feat: configure GitLab source via PUT /config"
```

---

### Task 3: Tests para GitLabSource con mock httpx

**Files:**
- Create: `daemon/tests/test_gitlab_source.py`

**Step 1: Write tests**

Create `daemon/tests/test_gitlab_source.py`:

```python
"""Tests para GitLabSource con mock de httpx."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from mimir_daemon.sources.gitlab import GitLabSource


def _mock_response(data, status_code=200):
    """Crea una respuesta httpx mock."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_get_issues_returns_parsed_data():
    """get_issues devuelve issues con project_path."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    mock_data = [
        {
            "id": 1, "iid": 42, "title": "Fix bug",
            "state": "opened", "web_url": "https://gitlab.test/group/project/-/issues/42",
            "references": {"full": "group/project#42"},
            "labels": ["bug"], "assignees": [],
            "milestone": None, "due_date": None,
            "created_at": "2026-03-01T10:00:00Z",
            "updated_at": "2026-03-13T15:00:00Z",
            "user_notes_count": 2,
        }
    ]

    # Mock: primera página tiene datos, segunda vacía
    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response(mock_data),
        _mock_response([]),
    ])

    issues = await source.get_issues()
    assert len(issues) == 1
    assert issues[0]["title"] == "Fix bug"
    assert issues[0]["_type"] == "issue"
    assert issues[0]["project_path"] == "group/project#42"


@pytest.mark.asyncio
async def test_get_merge_requests_deduplicates():
    """get_merge_requests deduplica MRs que aparecen en ambos scopes."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    mr = {
        "id": 10, "iid": 7, "title": "feat: auth",
        "state": "opened", "web_url": "https://gitlab.test/group/project/-/merge_requests/7",
        "references": {"full": "group/project!7"},
        "labels": [], "assignees": [], "reviewers": [],
        "source_branch": "feat/auth", "target_branch": "main",
        "has_conflicts": False, "pipeline_status": "success",
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-13T12:00:00Z",
        "user_notes_count": 1,
    }

    # assigned_to_me: 1 página con datos, 1 vacía; reviewer: 1 con mismo MR, 1 vacía
    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response([mr]),    # assigned_to_me page 1
        _mock_response([]),      # assigned_to_me page 2
        _mock_response([mr]),    # reviewer page 1 (same MR)
        _mock_response([]),      # reviewer page 2
    ])

    mrs = await source.get_merge_requests()
    assert len(mrs) == 1  # Deduplicado


@pytest.mark.asyncio
async def test_get_issues_handles_error():
    """get_issues propaga error si la API falla."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    source._client = MagicMock()
    source._client.get = AsyncMock(side_effect=[
        _mock_response([], status_code=401),
    ])

    with pytest.raises(httpx.HTTPStatusError):
        await source.get_issues()


@pytest.mark.asyncio
async def test_get_issues_empty():
    """get_issues devuelve lista vacía si no hay issues."""
    source = GitLabSource(url="https://gitlab.test", token="test-token")

    source._client = MagicMock()
    source._client.get = AsyncMock(return_value=_mock_response([]))

    issues = await source.get_issues()
    assert issues == []
```

**Step 2: Run tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_gitlab_source.py -v`
Expected: ALL PASS

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add daemon/tests/test_gitlab_source.py
git commit -m "test: add GitLabSource tests with httpx mocks"
```

---

### Task 4: Frontend — polling en IssuesView

**Files:**
- Modify: `src/views/IssuesView.vue`

**Step 1: Update IssuesView**

Rewrite the `<script setup>` to add refresh button and polling:

```typescript
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useIssuesStore } from '../stores/issues';
import { useConfigStore } from '../stores/config';
import FilterBar from '../components/shared/FilterBar.vue';
import IssueTable from '../components/issues/IssueTable.vue';

const issuesStore = useIssuesStore();
const configStore = useConfigStore();
const refreshing = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  issuesStore.fetchIssues();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

function startPolling() {
  stopPolling();
  const interval = (configStore.config.refresh_interval_seconds || 300) * 1000;
  pollTimer = setInterval(() => {
    issuesStore.fetchIssues();
  }, interval);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    await issuesStore.fetchIssues();
  } finally {
    refreshing.value = false;
  }
}
</script>
```

Update the template to add a toolbar with refresh button:

```html
<template>
  <div class="issues-view">
    <div class="view-toolbar">
      <FilterBar
        v-model="issuesStore.filterText"
        placeholder="Filtrar issues por titulo, proyecto o label..."
      />
      <button
        class="btn btn-ghost"
        @click="refresh"
        :disabled="refreshing || issuesStore.loading"
        title="Refrescar"
      >
        &#x21bb;
      </button>
    </div>

    <div v-if="issuesStore.error" class="error-banner">
      {{ issuesStore.error }}
    </div>

    <div v-if="issuesStore.loading && issuesStore.issues.length === 0" class="loading">
      Cargando issues...
    </div>

    <template v-else>
      <div
        v-for="(issues, project) in issuesStore.groupedIssues"
        :key="project"
        class="project-group"
      >
        <h3 class="project-name">{{ project }} ({{ issues.length }})</h3>
        <IssueTable :issues="issues" />
      </div>

      <div v-if="issuesStore.filteredIssues.length === 0 && !issuesStore.loading" class="empty-state">
        Sin issues que mostrar
      </div>
    </template>
  </div>
</template>
```

Add toolbar styles:

```css
.view-toolbar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
}

.view-toolbar .filter-bar {
  flex: 1;
  margin-bottom: 0;
}

.btn {
  padding: 6px 14px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  padding: 6px 10px;
}

.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
  background: var(--bg-hover);
}
```

**Step 2: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Commit**

```bash
git add src/views/IssuesView.vue
git commit -m "feat: add refresh button and polling to IssuesView"
```

---

### Task 5: Frontend — polling en MergeRequestsView

**Files:**
- Modify: `src/views/MergeRequestsView.vue`

**Step 1: Update MergeRequestsView**

Same pattern as IssuesView. Rewrite `<script setup>`:

```typescript
<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useMergeRequestsStore } from '../stores/merge_requests';
import { useConfigStore } from '../stores/config';
import FilterBar from '../components/shared/FilterBar.vue';
import MRTable from '../components/merge_requests/MRTable.vue';

const mrStore = useMergeRequestsStore();
const configStore = useConfigStore();
const refreshing = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  mrStore.fetchMergeRequests();
  startPolling();
});

onUnmounted(() => {
  stopPolling();
});

function startPolling() {
  stopPolling();
  const interval = (configStore.config.refresh_interval_seconds || 300) * 1000;
  pollTimer = setInterval(() => {
    mrStore.fetchMergeRequests();
  }, interval);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    await mrStore.fetchMergeRequests();
  } finally {
    refreshing.value = false;
  }
}
</script>
```

Update template:

```html
<template>
  <div class="mr-view">
    <div class="view-toolbar">
      <FilterBar
        v-model="mrStore.filterText"
        placeholder="Filtrar MRs por titulo, proyecto o rama..."
      />
      <button
        class="btn btn-ghost"
        @click="refresh"
        :disabled="refreshing || mrStore.loading"
        title="Refrescar"
      >
        &#x21bb;
      </button>
    </div>

    <div v-if="mrStore.error" class="error-banner">
      {{ mrStore.error }}
    </div>

    <div v-if="mrStore.loading && mrStore.mergeRequests.length === 0" class="loading">
      Cargando merge requests...
    </div>

    <template v-else>
      <div
        v-for="(mrs, project) in mrStore.groupedMRs"
        :key="project"
        class="project-group"
      >
        <h3 class="project-name">{{ project }} ({{ mrs.length }})</h3>
        <MRTable :merge-requests="mrs" />
      </div>

      <div v-if="mrStore.filteredMRs.length === 0 && !mrStore.loading" class="empty-state">
        Sin merge requests que mostrar
      </div>
    </template>
  </div>
</template>
```

Add same toolbar styles as IssuesView.

**Step 2: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Commit**

```bash
git add src/views/MergeRequestsView.vue
git commit -m "feat: add refresh button and polling to MergeRequestsView"
```

---

### Task 6: SettingsView — mostrar estado GitLab

**Files:**
- Modify: `src/views/SettingsView.vue`

**Step 1: Update SettingsView**

In the Daemon fieldset, in the Integraciones section, after the Odoo badge, add a GitLab badge:

```html
            <span class="integration-badge"
              :class="gitlabIntegrationConfigured ? 'configured' : 'not-configured'">
              GitLab: {{ gitlabIntegrationConfigured ? 'Conectado' : 'No configurado' }}
            </span>
```

Add the computed:

```typescript
const gitlabIntegrationConfigured = computed((): boolean => {
  const gitlab = integrationStatus.value?.gitlab;
  if (gitlab && typeof gitlab === 'object') {
    return Boolean((gitlab as Record<string, unknown>).configured);
  }
  return false;
});
```

**Step 2: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Commit**

```bash
git add src/views/SettingsView.vue
git commit -m "feat: show GitLab integration status in Settings"
```

---

### Task 7: Verificación final + PROGRESS.md

**Step 1: Run all daemon tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS (~108 tests)

**Step 2: Run TypeScript check**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 3: Run Rust check**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 4: Update PROGRESS.md**

Add Fase 5 section as COMPLETADA with all tasks and test counts.

**Step 5: Commit**

```bash
git add PROGRESS.md
git commit -m "docs: mark Phase 5 (GitLab views) as complete"
```
