# Plan: Generación de bloques bajo demanda — IMPLEMENTADO

## Resumen

Cambiar la generación de bloques de automática (SignalAggregator) a bajo demanda. El usuario pulsa un botón en ReviewDay, se invoca un agente Claude Code CLI que recopila señales + actividad VCS + Google Calendar + proyectos Odoo, y devuelve bloques estructurados como propuesta editable.

## Decisiones de diseño

1. **Señales siguen capturándose** cada 30s (mimir-capture no cambia), pero ya NO generan bloques automáticamente
2. **Generación incremental**: bloques `confirmed`/`synced`/`error` nunca se tocan. Bloques `auto`/`closed` se reemplazan al regenerar
3. **Reuniones = bloque propio**. Calendar da el nombre, señales `is_meeting=true` dan la duración real. Actividad VCS durante la reunión enriquece la descripción
4. **Eventos VCS**: se traen TODOS los tipos (push, comentarios, issues, MRs, aprobaciones...) y se agrupan por proyecto
5. **Señales = verdad para el tiempo**. VCS y Calendar dan el contexto (qué hiciste), señales dan la duración (cuánto tiempo)
6. **Matching a Odoo via Claude Code CLI**: el agente analiza URLs, repos, ramas, señales y asigna proyecto + tarea Odoo. El usuario siempre revisa y tiene la última decisión
7. **Claude Code CLI** como motor de IA (no API keys): se invoca un agente custom con instrucciones deterministas. Sin coste adicional de tokens
8. **UI**: botón "Generar bloques" en ReviewDay, loading ~30-60s, bloques aparecen como draft editable

## Arquitectura

```
Usuario pulsa "Generar bloques"
    │
    ▼
Frontend (ReviewDay) ──invoke()──▶ Tauri command (Rust)
    │
    ▼
Tauri spawns: claude --print --agent-prompt .claude/agents/timesheet-generator.md
              -p "Genera bloques para {fecha}"
    │
    ▼
Claude Code CLI (agente timesheet-generator):
    ├── 1. sqlite3: leer señales del día
    ├── 2. sqlite3: leer proyectos/tareas Odoo configurados
    ├── 3. sqlite3: leer tokens VCS (source_tokens)
    ├── 4. curl: actividad usuario GitLab (GET /users/{id}/events?after=date)
    ├── 5. curl: actividad usuario GitHub (GET /users/{username}/events)
    ├── 6. curl: eventos Google Calendar del día
    ├── 7. Cruzar todo → generar bloques JSON
    └── 8. stdout: JSON estructurado
    │
    ▼
Tauri parsea JSON ──HTTP POST──▶ mimir-server: /blocks/generate
    │
    ▼
Server crea bloques en SQLite (status="auto", preservando confirmed/synced)
    │
    ▼
Frontend recarga bloques → usuario edita/confirma/imputa
```

## Fases de implementación

### Fase 1: Agente Claude Code CLI
**Archivos nuevos:**
- `.claude/agents/timesheet-generator.md` — instrucciones del agente

**Contenido del agente:**
- Instrucciones paso a paso (deterministas)
- Queries SQL exactas para leer señales, proyectos Odoo, tokens
- Formato JSON de salida esperado
- Reglas de agrupación:
  - Señales con `is_meeting=true` consecutivas → bloque reunión
  - Cruzar con Calendar para obtener nombre de reunión
  - Eventos VCS agrupados por proyecto/repo
  - Señales asignadas a bloques VCS por coincidencia de `project_path`/`context_key`
  - Señales sin match VCS → bloque standalone
- Reglas de matching Odoo:
  - Comparar repos, URLs, ramas con nombres de proyectos/tareas Odoo
  - Consultar context_mappings existentes como referencia
  - Proponer proyecto + tarea con confianza

### Fase 2: Endpoints nuevos en mimir-server
**Archivos modificados:**
- `daemon/mimir_daemon/routers/blocks.py` — nuevo endpoint

**Endpoint:**
- `POST /blocks/generate` — recibe JSON del agente, crea bloques
  - Borra bloques `auto`/`closed` del día
  - Crea bloques nuevos desde el JSON
  - Preserva bloques `confirmed`/`synced`/`error`
  - Retorna bloques creados

### Fase 3: Nuevo endpoint Google Calendar
**Archivos modificados:**
- `daemon/mimir_daemon/integrations/google_calendar.py` — método `get_events_by_date()`
- `daemon/mimir_daemon/routers/google.py` — endpoint `GET /google/calendar/events?date=`

**Funcionalidad:**
- Obtener todos los eventos de un día (no solo el actual)
- El agente Claude Code puede llamar a este endpoint o directamente via curl con el token

### Fase 4: Actividad VCS del usuario
**Archivos modificados:**
- `daemon/mimir_daemon/sources/gitlab.py` — método `get_user_events(date)`
- `daemon/mimir_daemon/sources/github.py` — método `get_user_events(date)`
- `daemon/mimir_daemon/routers/vcs.py` — endpoints nuevos

**Endpoints:**
- `GET /gitlab/user/events?date=YYYY-MM-DD` — actividad del usuario en GitLab
- `GET /github/user/events?date=YYYY-MM-DD` — actividad del usuario en GitHub

**Nota:** El agente Claude Code podría hacer las llamadas directamente con curl, pero tener endpoints en el server permite reutilizarlos y testearlos.

### Fase 5: Comando Tauri + invocación CLI
**Archivos modificados:**
- `src-tauri/src/commands.rs` (o equivalente) — comando `generate_blocks`

**Funcionalidad:**
- Spawn proceso `claude --print ...`
- Capturar stdout (JSON)
- Parsear y enviar a `POST /blocks/generate`
- Devolver resultado al frontend

### Fase 6: Desactivar generación automática de bloques
**Archivos modificados:**
- `daemon/mimir_daemon/signal_aggregator.py` — desactivar creación de bloques

**Cambio:**
- `process_signal()` solo guarda la señal en SQLite, ya NO crea/actualiza/cierra bloques
- Mantener la tabla `block_signals` para el futuro
- Mantener `context_mappings` y `context_affinity` (el agente los consulta)

### Fase 7: UI — Botón en ReviewDay
**Archivos modificados:**
- `src/views/ReviewDayView.vue` — botón "Generar bloques"
- `src/stores/blocks.ts` — acción `generateBlocks(date)`

**Funcionalidad:**
- Botón en ViewToolbar: "Generar bloques"
- Estado loading con spinner (~30-60s)
- Al completar: recarga bloques del día
- Si hay bloques confirmed/synced: mostrar aviso de que esos se preservan

## JSON de salida del agente

```json
{
  "date": "2026-03-27",
  "blocks": [
    {
      "start_time": "2026-03-27T09:00:00",
      "end_time": "2026-03-27T09:40:00",
      "duration_minutes": 40,
      "type": "meeting",
      "description": "Daily standup — discusión sobre sprint review",
      "odoo_project_id": 5,
      "odoo_project_name": "Mimir",
      "odoo_task_id": 12,
      "odoo_task_name": "Reuniones",
      "confidence": 0.85,
      "sources": {
        "calendar_event": "Daily standup",
        "calendar_attendees": ["alice@empresa.com", "bob@empresa.com"],
        "signals_count": 80,
        "signals_meeting_count": 80,
        "vcs_events": []
      }
    },
    {
      "start_time": "2026-03-27T09:40:00",
      "end_time": "2026-03-27T12:00:00",
      "duration_minutes": 140,
      "type": "development",
      "description": "Refactor auth module — 3 commits, review MR#42",
      "odoo_project_id": 5,
      "odoo_project_name": "Mimir",
      "odoo_task_id": 34,
      "odoo_task_name": "Desarrollo backend",
      "confidence": 0.92,
      "sources": {
        "calendar_event": null,
        "calendar_attendees": null,
        "signals_count": 280,
        "signals_meeting_count": 0,
        "vcs_events": [
          {"type": "push", "detail": "3 commits en feat/auth", "repo": "mimir", "time": "10:30"},
          {"type": "comment", "detail": "Comentario en MR#42", "repo": "mimir", "time": "11:15"},
          {"type": "approve", "detail": "Aprobación MR#42", "repo": "mimir", "time": "11:45"}
        ]
      }
    }
  ]
}
```

## Orden de implementación recomendado

1. **Fase 1** — Agente (el cerebro, se puede testear manualmente con `claude --print`)
2. **Fase 6** — Desactivar generación automática (para no tener conflictos)
3. **Fase 3 + 4** — Endpoints Calendar + VCS (datos que necesita el agente)
4. **Fase 2** — Endpoint `/blocks/generate` (persistir resultado del agente)
5. **Fase 5** — Comando Tauri (conectar agente con servidor)
6. **Fase 7** — UI (botón + loading + recarga)

## Testing

- **Agente**: ejecutar manualmente y verificar JSON de salida
- **Endpoints nuevos**: tests con mocks (patrón existente en daemon)
- **Integración**: test E2E desde botón UI → bloques creados
- **Regresión**: verificar que señales siguen capturándose correctamente
