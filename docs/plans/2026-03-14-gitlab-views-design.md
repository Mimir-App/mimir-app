# Fase 5 — Vistas GitLab: Diseño

## Resumen

Conectar GitLabSource existente con server.py, configurar via PUT /config, frontend con polling mientras vista activa. Scoring en frontend (ya implementado).

## Arquitectura

```
PUT /config (gitlab_url + token) → daemon configura GitLabSource en SourceRegistry
GET /gitlab/issues       → SourceRegistry.get_all_issues()       → GitLab API v4
GET /gitlab/merge_requests → SourceRegistry.get_all_merge_requests() → GitLab API v4
                                    ↓
Frontend: stores aplican scoring (TS), vistas agrupan por proyecto, polling periódico
```

## Lo que ya existe
- `sources/gitlab.py` — GitLabSource con get_issues/get_merge_requests
- `sources/registry.py` — SourceRegistry con get_all_issues/get_all_merge_requests
- Frontend completo: stores, vistas, tablas, scoring, ScoreBadge, FilterBar
- Rust commands: get_issues, get_merge_requests
- api.ts: getIssues(), getMergeRequests()

## Lo que falta
1. Conectar stubs en server.py con SourceRegistry
2. Configurar GitLabSource via PUT /config
3. Pasar SourceRegistry a create_app y main.py
4. integration-status para GitLab
5. Frontend: polling + botón refrescar en vistas
6. Tests daemon
