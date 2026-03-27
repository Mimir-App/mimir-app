# Reglas de imputacion

## Convenciones de ramas
Las ramas siguen el patron `<nombre_proyecto>_<num_tarea>`.
Ejemplos:
- `mm_545` → proyecto "masmusculo", tarea 545
- `gextia_8119` → proyecto "gextia/fl-v16", tarea 8119
- `fix_company_tax_groups` → no sigue el patron, buscar por nombre de proyecto

El numero de tarea en la rama es el numero real de la tarea en Odoo (campo iid o name).

## Reuniones
- **Daily / Standup**: proyecto "Temas internos", tarea "Daily"
- **Refinamiento**: proyecto "Temas internos", tarea "Refinamiento"
- **COP / Comunidad de practicas**: proyecto "Temas internos", tarea "Formacion impulsada"
- **Sprint review / Retro**: proyecto "Temas internos", tarea "Sprint review"

## Descripciones de MR
Las descripciones de los MRs suelen incluir la tarea asociada. Si la descripcion menciona un numero de tarea, usarlo.

## Proyectos conocidos
Mapeos entre nombres de repos/ramas y proyectos Odoo:
- `mm` / `masmusculo` → proyecto "masmusculo"
- `gextia` → proyecto "gextia/fl-v16"
- `connector-prestashop` / `prestashop` → proyecto "connector-prestashop"
- `autogestion-entornos` / `fl-devops` → proyecto "FL DevOps"
