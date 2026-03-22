# Issues/MRs Multi-Source Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar la experiencia de Issues y MRs para GitHub y GitLab: filtros por fuente, datos normalizados, score editable en tabla, labels con color, busqueda multi-source.

**Architecture:** Normalizar datos de GitHub en el adapter Python para que coincidan con el formato esperado por el frontend. Anadir campo `_source` a los tipos TS. Extender filtros y UI con iconos de fuente. Score editable directamente en la tabla.

**Tech Stack:** Python (daemon), TypeScript/Vue (frontend), Rust (Tauri commands)

---

## Problemas detectados

| Problema | Causa | Solucion |
|---|---|---|
| Score NaN | GitHub no tiene `user_notes_count`, usa `comments` | Normalizar en adapter |
| Assignees vacios | GitHub usa `login` en vez de `username` | Normalizar en adapter |
| Labels sin color | Frontend renderiza `<span>` plano | Pasar objetos `{name, color}` y pintar |
| Milestone raro | GitHub devuelve objeto `{title, ...}`, GitLab string | Normalizar a string |
| Sin filtro por fuente | No existe `_source` en tipos TS | Anadir y filtrar |
| Score no editable en tabla | Solo editable en modal detalle | ScoreBadge editable |
| Busqueda solo GitLab | `searchGitlabIssues` hardcoded | Busqueda multi-source con filtro |
| Boton modal generico | Dice "Ir a GitLab" siempre | Dinamico segun `_source` |

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `daemon/mimir_daemon/sources/github.py` | Normalizar campos: `user_notes_count`, `username`, `milestone`, `due_date`, `labels` |
| `src/lib/types.ts` | Anadir `_source` a GitLabIssue y GitLabMergeRequest, labels como `{name,color}[]` |
| `src/lib/scoring.ts` | Manejar `user_notes_count` undefined (fallback 0) |
| `src/components/shared/ScoreBadge.vue` | Modo editable con emit |
| `src/components/issues/IssueTable.vue` | Icono fuente, labels con color, score editable |
| `src/components/merge_requests/MRTable.vue` | Icono fuente, labels con color, score editable |
| `src/components/issues/IssueDetailModal.vue` | Boton dinamico, icono fuente |
| `src/components/merge_requests/MRDetailModal.vue` | Boton dinamico, icono fuente |
| `src/stores/issues.ts` | Filtro por fuente, busqueda multi-source |
| `src/stores/merge_requests.ts` | Filtro por fuente, busqueda multi-source |
| `src/views/IssuesView.vue` | Filtro tabs fuente, busqueda con selector |
| `src/views/MergeRequestsView.vue` | Filtro tabs fuente, busqueda con selector |
| `src/lib/api.ts` | Endpoint busqueda GitHub |
| `src-tauri/src/commands/daemon.rs` | Tauri commands busqueda GitHub |
| `src-tauri/src/lib.rs` | Registrar commands |

---

### Task 1: Normalizar datos GitHub en el adapter Python

**Files:**
- Modify: `daemon/mimir_daemon/sources/github.py`

**Objetivo:** Que los datos de GitHub tengan los mismos campos que GitLab para que el frontend funcione sin condicionales.

- [ ] **Step 1: Normalizar `get_issues()`**

Anadir a cada issue devuelto:
```python
# Campos que GitLab tiene y GitHub no
item["user_notes_count"] = item.get("comments", 0)
item["due_date"] = None  # GitHub no tiene due_date en issues
item["has_conflicts"] = False
item["manual_priority"] = None
item["description"] = item.get("body", "")
# Milestone: GitHub devuelve objeto, normalizar a string
ms = item.get("milestone")
item["milestone"] = ms.get("title") if isinstance(ms, dict) else ms
# Labels: GitHub devuelve objetos, necesitamos ambos formatos
raw_labels = item.get("labels", [])
item["label_objects"] = [{"name": l["name"], "color": l.get("color", "")} for l in raw_labels if isinstance(l, dict)]
item["labels"] = [l["name"] if isinstance(l, dict) else l for l in raw_labels]
# Assignees: normalizar username
for a in item.get("assignees", []):
    if "username" not in a:
        a["username"] = a.get("login", "")
```

- [ ] **Step 2: Normalizar `get_merge_requests()`**

Mismos campos + campos especificos de MR:
```python
item["user_notes_count"] = item.get("comments", 0)
item["has_conflicts"] = False  # GitHub no expone en search
item["pipeline_status"] = None
item["source_branch"] = item.get("head", {}).get("ref", "") if isinstance(item.get("head"), dict) else ""
item["target_branch"] = item.get("base", {}).get("ref", "") if isinstance(item.get("base"), dict) else ""
item["reviewers"] = []
item["manual_priority"] = None
item["description"] = item.get("body", "")
# Milestone y labels igual que issues
```

- [ ] **Step 3: Normalizar `search_issues()` y `search_pull_requests()`**

Misma normalizacion que los metodos principales.

- [ ] **Step 4: Verificar con curl**

```bash
curl -s http://127.0.0.1:9477/gitlab/issues | python3 -c "
import json, sys
for i in json.load(sys.stdin):
    print(i.get('_source'), i.get('user_notes_count'), i.get('milestone'), type(i.get('labels')).__name__)
"
```

- [ ] **Step 5: Tests**

```bash
cd daemon && python3 -m pytest tests/ --tb=short
```

---

### Task 2: Normalizar datos GitLab (labels con color)

**Files:**
- Modify: `daemon/mimir_daemon/sources/gitlab.py`

**Objetivo:** Que GitLab tambien devuelva `label_objects` con color para que las labels se pinten.

- [ ] **Step 1: Anadir `label_objects` a issues y MRs de GitLab**

GitLab ya devuelve labels como strings. Necesitamos pedir los objetos completos. En `get_issues()` y `get_merge_requests()`, las labels vienen como strings en la respuesta principal. Podemos:
- Opcion A: Pedir labels como objetos (GitLab API soporta `with_labels_details=true` en issues)
- Opcion B: Mantener strings y cargar colores desde el endpoint `/labels`

Opcion B es mas simple — en el frontend se hara un mapa de colores desde `/gitlab/labels`.

- [ ] **Step 2: No tocar el adapter, resolver en frontend**

Crear un mapa `labelName -> color` en el store y pasarlo a los componentes.

---

### Task 3: Tipos TypeScript — anadir `_source` y `label_objects`

**Files:**
- Modify: `src/lib/types.ts`

- [ ] **Step 1: Actualizar interfaces**

```typescript
export interface LabelInfo {
  name: string;
  color: string;
}

export interface GitLabIssue {
  // ... campos existentes ...
  _source?: 'gitlab' | 'github';
  label_objects?: LabelInfo[];
}

export interface GitLabMergeRequest {
  // ... campos existentes ...
  _source?: 'gitlab' | 'github';
  label_objects?: LabelInfo[];
}
```

---

### Task 4: Fix scoring para campos opcionales

**Files:**
- Modify: `src/lib/scoring.ts`

- [ ] **Step 1: Usar fallbacks seguros**

```typescript
export function computeIssueScore(issue: GitLabIssue): number {
  const manual = issue.manual_priority ?? 0;
  const label = scoreLabelPriority(issue.labels ?? []);
  const state = scoreStateMilestone(issue.state, issue.milestone ?? null);
  const comments = scoreComments(issue.user_notes_count ?? 0);
  const due = scoreDueDate(issue.due_date ?? null);
  return manual + label + state + comments + due;
}

export function computeMRScore(mr: GitLabMergeRequest): number {
  const manual = mr.manual_priority ?? 0;
  const label = scoreLabelPriority(mr.labels ?? []);
  const state = scoreStateMilestone(mr.state, null);
  const comments = scoreComments(mr.user_notes_count ?? 0);
  const conflicts = mr.has_conflicts ? WEIGHTS.MR_CONFLICTS : 0;
  const pipeline = mr.pipeline_status === 'failed' ? WEIGHTS.FAILED_PIPELINE : 0;
  return manual + label + state + comments + conflicts + pipeline;
}
```

---

### Task 5: ScoreBadge editable

**Files:**
- Modify: `src/components/shared/ScoreBadge.vue`

- [ ] **Step 1: Anadir modo editable**

Props: `score: number`, `editable?: boolean`, `manualScore?: number`
Emit: `update:manualScore(value: number)`

Al hacer click (si editable): mostrar un input numerico inline.
Al perder foco o Enter: emit el nuevo valor.
Mostrar score total + indicador de manual score si > 0.

---

### Task 6: Labels con color en tablas

**Files:**
- Modify: `src/components/issues/IssueTable.vue`
- Modify: `src/components/merge_requests/MRTable.vue`

- [ ] **Step 1: Pintar labels con color**

```html
<span
  v-for="label in issue.label_objects?.slice(0, 3) ?? issue.labels.slice(0, 3).map(l => ({ name: l, color: '' }))"
  :key="label.name"
  class="label-tag"
  :style="label.color ? { background: label.color + '33', color: label.color, borderColor: label.color } : {}"
>{{ label.name }}</span>
```

- [ ] **Step 2: Anadir icono de fuente**

Columna extra estrecha con icono:
- GitLab: circulo naranja con "GL"
- GitHub: circulo blanco con "GH"

Basado en `issue._source`.

- [ ] **Step 3: Score editable en tabla**

Reemplazar `<ScoreBadge :score="issue.score" />` por:
```html
<ScoreBadge
  :score="issue.score"
  :manual-score="issue.manual_priority ?? 0"
  editable
  @update:manual-score="(v) => onUpdateScore(issue.id, v)"
/>
```

---

### Task 7: Filtro por fuente en stores

**Files:**
- Modify: `src/stores/issues.ts`
- Modify: `src/stores/merge_requests.ts`

- [ ] **Step 1: Anadir `sourceFilter` al state**

```typescript
const sourceFilter = ref<'all' | 'gitlab' | 'github'>('all');
```

- [ ] **Step 2: Aplicar filtro en computed**

En `filteredIssues`, antes del filtro de texto:
```typescript
if (sourceFilter.value !== 'all') {
  result = result.filter(i => (i as any)._source === sourceFilter.value);
}
```

---

### Task 8: Busqueda multi-source

**Files:**
- Modify: `src/stores/issues.ts`
- Modify: `src/stores/merge_requests.ts`
- Modify: `src/lib/api.ts`
- Modify: `src-tauri/src/commands/daemon.rs`
- Modify: `src-tauri/src/lib.rs`

- [ ] **Step 1: Anadir endpoints API para busqueda GitHub**

En `api.ts`:
```typescript
async searchGithubIssues(q: string): Promise<GitLabIssue[]> {
  if (await isTauri()) return tauriInvoke('search_github_issues', { q });
  return httpGet(`/github/issues/search?q=${encodeURIComponent(q)}`);
},
async searchGithubPullRequests(q: string): Promise<GitLabMergeRequest[]> {
  if (await isTauri()) return tauriInvoke('search_github_pull_requests', { q });
  return httpGet(`/github/pull_requests/search?q=${encodeURIComponent(q)}`);
},
```

- [ ] **Step 2: Tauri commands**

```rust
#[tauri::command]
pub async fn search_github_issues(q: String) -> Result<Vec<serde_json::Value>, String> {
    get_client().get(&format!("/github/issues/search?q={}", urlencoding::encode(&q))).await
}
#[tauri::command]
pub async fn search_github_pull_requests(q: String) -> Result<Vec<serde_json::Value>, String> {
    get_client().get(&format!("/github/pull_requests/search?q={}", urlencoding::encode(&q))).await
}
```

Registrar en `lib.rs`.

- [ ] **Step 3: Busqueda unificada en store**

```typescript
async function searchIssues(query: string, source: 'all' | 'gitlab' | 'github' = 'all') {
  searchLoading.value = true;
  try {
    const results: GitLabIssue[] = [];
    if (source !== 'github') results.push(...await api.searchGitlabIssues(query));
    if (source !== 'gitlab') results.push(...await api.searchGithubIssues(query));
    searchResults.value = results;
  } finally {
    searchLoading.value = false;
  }
}
```

---

### Task 9: Filtro y busqueda en vistas

**Files:**
- Modify: `src/views/IssuesView.vue`
- Modify: `src/views/MergeRequestsView.vue`

- [ ] **Step 1: Anadir tabs de fuente**

Junto a los filtros existentes (Todas/Asignadas/Seguidas), anadir selector de fuente:
```
[Todas] [GitLab] [GitHub]
```

Usando `CustomSelect` o botones simples. Controla `issuesStore.sourceFilter`.

- [ ] **Step 2: Selector de fuente en busqueda**

Junto al input de busqueda, un dropdown `[Todas | GitLab | GitHub]` que se pasa al `searchIssues()`.

---

### Task 10: Modal detalle dinamico

**Files:**
- Modify: `src/components/issues/IssueDetailModal.vue`
- Modify: `src/components/merge_requests/MRDetailModal.vue`

- [ ] **Step 1: Boton dinamico**

```html
<a :href="issue.web_url" target="_blank">
  Ir a {{ issue._source === 'github' ? 'GitHub' : 'GitLab' }}
</a>
```

- [ ] **Step 2: Icono de fuente en header del modal**

Mostrar el icono de fuente junto al titulo.

---

### Task 11: Verificacion final

- [ ] **Step 1: TypeScript check**
```bash
npx vue-tsc --noEmit
```

- [ ] **Step 2: Rust check**
```bash
cd src-tauri && cargo check
```

- [ ] **Step 3: Python tests**
```bash
cd daemon && python3 -m pytest tests/ --tb=short
```

- [ ] **Step 4: Test manual**
- Verificar issues de GitHub se muestran con icono GH
- Verificar score no es NaN
- Verificar filtro por fuente funciona
- Verificar busqueda en ambas fuentes
- Verificar labels con color
- Verificar score editable desde tabla
- Verificar boton modal dice "Ir a GitHub" / "Ir a GitLab"
