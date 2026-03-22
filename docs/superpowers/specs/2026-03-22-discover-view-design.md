# Discover View — Design Spec

**Fecha:** 2026-03-22
**Autor:** Jesus Lorenzo + Claude

## Objetivo

Crear una vista "Descubrir" que sirva como buscador universal de issues y MRs/PRs en GitHub y GitLab. Separar la busqueda global de la vista de Issues (que queda para items asignados/seguidos). Desde Descubrir se puede explorar, ver detalle y seguir items.

## Contexto

Actualmente la busqueda global esta dentro de IssuesView con un dropdown que muestra resultados de todas las fuentes. Esto genera ruido (resultados de repos ajenos) y no permite filtrar antes de buscar. La vista de Issues debe mostrar solo lo que el usuario tiene asignado o sigue.

## Componentes

### 1. Ruta y navegacion

- Nueva ruta `/discover` en el router
- Nueva entrada "Descubrir" en `AppSidebar` con icono de lupa
- Posicion: despues de "MRs" y antes de "Timesheets"

### 2. DiscoverView.vue (`src/views/DiscoverView.vue`)

Vista principal. No usa store propio — estado local porque es exploracion efimera.

**Estado:**
- `source: 'all' | 'github' | 'gitlab'` — filtro fuente
- `itemType: 'all' | 'issue' | 'mr'` — filtro tipo
- `repo: string` — filtro repositorio (vacio = todos)
- `query: string` — texto de busqueda
- `limit: number` — max resultados a mostrar (default 20)
- `results: Array` — resultados de la busqueda
- `totalCount: number` — total de resultados encontrados
- `loading: boolean`

**Barra de filtros (horizontal):**
```
[Fuente ▼] [Tipo ▼] [Repo ▼] [___buscar___] [Limite ▼] | Mostrando N de M
```

- Fuente: select con opciones dinamicas (solo las conectadas + "Todas" si hay mas de una)
- Tipo: select `Todos | Issues | MRs/PRs`
- Repo: select con autocomplete. Opciones: repos conocidos (de issues cargadas en issuesStore + mrStore). Escribir para filtrar.
- Input: texto libre, busqueda debounced 300ms
- Limite: select `10 | 20 | 50 | 100`
- Contador: "Mostrando N de M resultados" o "Sin resultados"

**Tabla de resultados (DiscoverTable.vue):**
- Columnas: Icono fuente | # | Titulo | Repo | Labels (con color) | Autor | Fecha | Accion
- Titulo: click abre modal de detalle (IssueDetailModal o MRDetailModal segun `_type`)
- Accion: boton "Seguir" / "Siguiendo" (toggle)
- Click derecho: ContextMenu sin opciones de score

**Footer:**
- Boton "Mostrar mas" visible si `results.length < totalCount`
- Al pulsar: incrementa `limit` en la cantidad actual (20 mas) y re-ejecuta busqueda

### 3. DiscoverTable.vue (`src/components/discover/DiscoverTable.vue`)

Tabla de resultados reutilizable.

**Props:**
- `items: Array<GitLabIssue | GitLabMergeRequest>` — resultados
- `followedIds: Set<number>` — IDs seguidos

**Emits:**
- `select(item)` — abrir detalle
- `follow(itemId)` — seguir
- `unfollow(itemId)` — dejar de seguir
- `contextmenu(item, event)` — menu contextual

**Columnas:**
| Col | Ancho | Contenido |
|---|---|---|
| Icono | 24px | SourceIcon (github/gitlab) |
| Tipo | 24px | Icono issue/MR |
| # | auto | iid |
| Titulo | expand | Texto clickeable |
| Repo | 180px | project_path |
| Labels | 200px | Chips con color |
| Autor | 100px | username |
| Fecha | 100px | updated_at formateado |
| Accion | 80px | Boton Seguir/Siguiendo |

### 4. Logica de busqueda

La busqueda se dispara cuando:
- El usuario escribe >= 2 caracteres (debounce 300ms)
- Cambia cualquier filtro (fuente, tipo, repo)
- Pulsa "Mostrar mas"

**Flujo:**
1. Construir query: si hay repo, prepend `repo:owner/name`
2. Segun `source` y `itemType`, llamar a los endpoints correspondientes:
   - `all` + `all`: buscar issues + MRs en ambas fuentes (4 llamadas en paralelo)
   - `github` + `issue`: solo `api.searchGithubIssues(query)`
   - etc.
3. Combinar resultados, ordenar por `updated_at` desc
4. Cortar a `limit`
5. Actualizar `totalCount` con el total antes del corte

**Endpoints usados (ya existentes):**
- `api.searchGitlabIssues(q)`
- `api.searchGithubIssues(q)`
- `api.searchGitlabMergeRequests(q)` (existe en api.ts como `searchGitlabMergeRequests` — verificar, si no crear)
- `api.searchGithubPullRequests(q)`

### 5. Menu contextual

Reutiliza `ContextMenu.vue`. Items (sin score):
- Ver detalle
- Ir a GitHub/GitLab (segun `_source`)
- Seguir / Dejar de seguir
- Copiar enlace
- Copiar referencia (`proyecto#iid`)

### 6. Limpieza de IssuesView

- Eliminar la seccion de busqueda global (search bar + dropdown)
- Mantener solo el filtro de texto local (ViewToolbar) para filtrar issues ya cargadas
- La busqueda ahora vive en Descubrir

## Fuera de alcance

- Vista Kanban/cards (futuro)
- Busqueda de repos o usuarios (futuro)
- Store persistente para resultados de busqueda
- Paginacion real de API (usamos client-side limit por ahora)

## Archivos

| Archivo | Accion |
|---|---|
| `src/views/DiscoverView.vue` | Crear |
| `src/components/discover/DiscoverTable.vue` | Crear |
| `src/router/index.ts` | Modificar — anadir ruta `/discover` |
| `src/components/layout/AppSidebar.vue` | Modificar — anadir entrada "Descubrir" |
| `src/views/IssuesView.vue` | Modificar — eliminar busqueda global |
| `src/lib/api.ts` | Verificar/crear `searchGitlabMergeRequests` |
| `src-tauri/src/commands/daemon.rs` | Verificar Tauri command para search MRs GitLab |
