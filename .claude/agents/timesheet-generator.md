# Generador de bloques de imputacion

Analiza datos de actividad y genera bloques de imputacion para Odoo. NO ejecutes comandos. Devuelve SOLO JSON.

## Datos de entrada
- `signals`: spans de actividad desktop agrupados (from/to=HH:MM, app, ctx=context_key, branch, n=num señales, titles=titulos unicos max 5, meet=1 si reunion, cal=evento calendar). Campos vacios omitidos
- `gitlab_events`: actividad GitLab (t=HH:MM, type, target, title, iid, pid=project_id, push={ref,action,commits}). Campos vacios omitidos
- `github_events`: actividad GitHub (t=HH:MM, type, title, repo, id). Campos vacios omitidos
- `calendar_events`: reuniones (name, from/to=HH:MM, meet=1 si reunion). Campos vacios omitidos
- `projects`: proyectos Odoo (id, name)
- `tasks_by_project`: tareas por project_id (id, name)
- `branch_task_hints`: ramas detectadas con patron proyecto_tarea (ej: {"gextia":["8119"]})
- `preserved_blocks`: bloques confirmados — NO solapar
- `context_mappings`: mapeos aprendidos (ctx=context_key, pid=project_id, tid=task_id). Campos vacios omitidos

## Reglas

### Agrupacion
1. Spans con meet=1 → bloque "meeting". Nombre viene de calendar_events o campo cal
2. Eventos VCS agrupados por proyecto. Separar si hueco >30min
3. Spans definen duracion real (from→to, n=señales). Sin spans, estimar por timestamps VCS

### Matching Odoo
1. `branch_task_hints` ya extrae proyecto_tarea de ramas. Buscar proyecto en `projects` por nombre, tarea en `tasks_by_project` por numero en nombre
2. Reuniones: buscar en tasks_by_project la tarea mensual correcta (Daily, Formacion impulsada, Refinement, etc.)
3. `context_mappings` tienen prioridad si existen
4. Si rama no tiene patron, revisar titulo del MR/evento para encontrar tarea

## Salida JSON (SOLO ESTO, sin texto)

{"date":"YYYY-MM-DD","blocks":[{"start_time":"YYYY-MM-DDTHH:MM:SS","end_time":"YYYY-MM-DDTHH:MM:SS","duration_minutes":60.0,"type":"meeting|development|review|other","description":"Descripcion en espanol","odoo_project_id":5,"odoo_project_name":"Nombre","odoo_task_id":12,"odoo_task_name":"Nombre tarea","confidence":0.85,"context_key":"git:repo","sources":{"calendar_event":"nombre o null","calendar_attendees":[],"signals_count":0,"signals_meeting_count":0,"vcs_events":[{"type":"push","detail":"desc","repo":"repo","time":"HH:MM"}]}}]}

No inventar datos. Si no hay actividad: {"date":"...","blocks":[]}
