# Mimir — Arquitectura de senales y bloques derivados

## Contexto

El sistema actual de captura crea bloques en tiempo real basandose solo en cambios de app o proyecto git. Esto produce bloques demasiado grandes (8h en la misma app) o demasiado pequenos (micro-bloques al alternar ventanas). Ademas, cambios dentro de una app (pestanas de navegador, ficheros en IDE) no generan bloques nuevos.

## Objetivo

Redisenar la captura para que:
1. Se capturen senales finas (cada poll = 1 senal cruda)
2. Los bloques se construyan automaticamente a partir de senales con un algoritmo determinista
3. La IA solo intervenga bajo demanda del usuario, nunca en la agrupacion automatica
4. Los bloques confirmados sean intocables para la IA (solo descripciones)
5. El usuario pueda ver los datos crudos (senales) en cualquier momento

## Modelo de datos

### Senal (dato crudo)

Una senal es un snapshot de lo que el usuario estaba haciendo en un instante.

```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,           -- ISO 8601 UTC
    app_name TEXT,                     -- de /proc/pid/comm
    window_title TEXT,                 -- titulo completo de la ventana
    project_path TEXT,                 -- ruta del proyecto git (o NULL)
    git_branch TEXT,
    git_remote TEXT,
    ssh_host TEXT,                     -- host SSH si aplica
    pid INTEGER,
    context_key TEXT,                  -- clave de contexto calculada (proyecto, dominio, o app)
    last_commit_message TEXT,          -- ultimo commit del proyecto git
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_signals_timestamp ON signals(timestamp);
```

Se genera 1 senal por poll (cada 30s). ~960 senales/dia en 8h de trabajo. Tamano negligible en SQLite.

### Bloque (dato derivado)

Los bloques siguen existiendo con el mismo esquema actual. La diferencia es que ahora se construyen a partir de senales, no directamente por el poller.

Tabla de relacion senales-bloques (permite split/merge sin perder trazabilidad):

```sql
CREATE TABLE block_signals (
    block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    signal_id INTEGER NOT NULL REFERENCES signals(id),
    PRIMARY KEY (block_id, signal_id)
);
```

### Ciclo de vida de un bloque

```
auto → closed → confirmed → synced
```

- `auto`: bloque abierto, el aggregator lo esta construyendo
- `closed`: el aggregator lo cerro (cambio de contexto o inactividad)
- `confirmed`: el usuario lo aprobo en "Revisar dia"
- `synced`: enviado a Odoo

El aggregator solo toca bloques `auto`. Los bloques `closed`, `confirmed` y `synced` son inmutables para el aggregator.

### Retencion de datos

Senales mas antiguas de 6 meses se eliminan automaticamente. Los bloques persisten indefinidamente.

## Flujo de datos

```
Poller (cada 30s)
  |
  v
Senal -> SQLite (signals)
  |
  v
SignalAggregator (tiempo real, determinista)
  |
  v
Bloques -> SQLite (blocks + block_signals)
  |
  v
Usuario revisa en "Revisar dia"
  |
  +-- Ve bloques agrupados (vista normal)
  +-- Ve senales crudas (vista detalle/verbose)
  +-- Confirma bloques (status: confirmed)
  +-- Pide a IA: descripciones, sugerir fusion/particion
```

## Componentes

### 1. Poller (modificado)

Ya no llama a BlockManager.process_poll(). En su lugar:
1. Captura ventana activa (igual que ahora)
2. Enriquece contexto (igual que ahora)
3. Calcula `context_key` para la senal
4. Guarda la senal en la tabla `signals`
5. Llama a `SignalAggregator.process_signal()` con la senal nueva

### 2. SignalAggregator (nuevo)

Ubicacion: `daemon/mimir_daemon/signal_aggregator.py`
Proceso: vive en mimir-capture (el mismo proceso que el poller).

Reemplaza al BlockManager como motor de agrupacion. Algoritmo determinista basado en reglas.

#### Reglas de agrupacion

Una senal pertenece al bloque actual si se cumple **todo**:

1. **Mismo contexto**: `signal.context_key == bloque_actual.context_key`
2. **Continuidad temporal**: no han pasado mas de N minutos desde la ultima senal del bloque (default: 5, configurable)

Si alguna condicion no se cumple, se cierra el bloque actual y se abre uno nuevo.

#### Definicion de context_key

El context_key se calcula por prioridad:

1. **Si hay proyecto git**: `context_key = "git:" + project_path`
2. **Si es navegador**: `context_key = "web:" + site_name` (extraido del titulo)
3. **Para todo lo demas**: `context_key = "app:" + app_name`

#### Extraccion de site_name del titulo del navegador

Estrategia:
1. Eliminar el nombre del navegador del final del titulo (usando BROWSER_APPS)
2. Separar el resultado por ` — `, ` – `, o ` - `
3. Tomar el ULTIMO segmento restante (que es normalmente el nombre del sitio)
4. Si no hay separador, usar el titulo completo

Ejemplos:
- `"Pull Request #42 · repo — GitHub — Google Chrome"` → strip "Google Chrome" → split por ` — ` → `["Pull Request #42 · repo", "GitHub"]` → ultimo: `"GitHub"` → context_key: `"web:GitHub"`
- `"Bandeja de entrada - Gmail — Google Chrome"` → strip "Google Chrome" → `"Bandeja de entrada - Gmail"` → split por ` - ` → `["Bandeja de entrada", "Gmail"]` → ultimo: `"Gmail"` → context_key: `"web:Gmail"`
- `"Stack Overflow"` (sin separador) → context_key: `"web:Stack Overflow"`

#### Lista de apps navegador

```python
BROWSER_APPS = {"chrome", "chromium", "firefox", "brave", "vivaldi", "opera", "microsoft-edge", "zen", "floorp"}
```

Configurable desde Settings.

#### Apps transitorias

Algunas apps no deben generar bloques propios (file managers, dialogs). Si la app actual esta en la lista de transitorias, la senal hereda el context_key de la senal anterior.

```python
TRANSIENT_APPS = {"nautilus", "thunar", "nemo", "pcmanfm", "dolphin"}
```

#### Manejo de inactividad y bloqueo

- Si pasan >N minutos sin senales (configurable, default: 5), se cierra el bloque actual.
- `handle_lock()`: cierra el bloque actual inmediatamente.
- `handle_unlock()`: la proxima senal abre un bloque nuevo.
- Al volver de inactividad, se abre bloque nuevo.

#### Bloques confirmados

Cuando el usuario confirma un bloque (`status: confirmed`), el SignalAggregator NO lo toca. Las senales nuevas que correspondan temporalmente a un bloque confirmado se vinculan via `block_signals` pero no modifican el bloque.

#### Crash recovery

Al arrancar, el aggregator consulta la DB:
1. Si hay un bloque `auto` sin cerrar, compara su ultimo timestamp con ahora
2. Si paso menos del umbral de inactividad, lo retoma como bloque activo
3. Si paso mas, lo cierra como `closed`

#### window_titles_json

Al cerrar un bloque, se genera `window_titles_json` a partir de las senales asociadas: los titulos unicos (hasta 20) ordenados por frecuencia. Esto mantiene compatibilidad con el sistema de descripciones IA.

### 3. BlockManager (eliminado)

Se reemplaza completamente por SignalAggregator. Las funciones de DB (`create_block`, `update_block`) ya estan en `Database`, no en `BlockManager`. No hay nada que conservar.

Nota: NO usar `from __future__ import annotations` en el nuevo archivo (convencion del proyecto).

### 4. API endpoints (server.py)

Nuevos endpoints:

```
GET  /signals?date=YYYY-MM-DD              — senales del dia
GET  /signals?block_id=N                   — senales de un bloque especifico
POST /blocks/{block_id}/split              — partir bloque en un signal_id
POST /blocks/merge                         — fusionar bloques {block_ids: [1, 2]}
```

Los endpoints existentes de bloques siguen funcionando igual.

### 5. Tauri commands (Rust)

Nuevos commands proxy para los endpoints:
- `get_signals(date, block_id)`
- `split_block(block_id, signal_id)`
- `merge_blocks(block_ids)`

### 6. Vista "Revisar dia" (modificada)

#### Vista normal (bloques)

Como ahora — tabla con bloques, pero con mejor granularidad gracias a las senales.

#### Vista detalle (senales crudas)

Nuevo toggle "Ver senales" (usando CollapsibleGroup) que muestra las senales del dia o de un bloque:
- Timestamp, app, titulo ventana, proyecto, context_key
- Cada fila es un poll de 30s
- Se resalta a que bloque pertenece cada senal (color o agrupacion visual)

#### Acciones del usuario sobre bloques

- **Confirmar**: marca el bloque como intocable (`status: confirmed`)
- **Partir**: divide un bloque en dos en un punto (signal_id). Los bloques resultantes son `closed`.
- **Fusionar**: junta dos o mas bloques consecutivos no confirmados en uno.
- **Editar**: cambiar descripcion, proyecto Odoo, tarea

### 7. IA (sin cambios en el trigger, cambios en el scope)

- **Descripciones**: puede generar/regenerar para cualquier bloque (confirmado o no). Recibe las senales del bloque como contexto en vez de solo `window_titles_json`.
- **Sugerir fusion/particion**: solo para bloques NO confirmados (`auto` o `closed`). El usuario aprueba o rechaza.

### 8. Status endpoint

El endpoint `/status` del capture incluye:
- `"backend": "x11"` o `"backend": "wayland"` (del platform layer)
- `"signals_today": N` (numero de senales del dia)

## Migracion

### Base de datos

1. Crear tabla `signals` con indice en timestamp
2. Crear tabla `block_signals`
3. Los bloques existentes no tienen senales asociadas — es correcto, se crearon con el sistema anterior
4. Migraciones con try/except para idempotencia (SQLite no soporta `IF NOT EXISTS` en ALTER TABLE)

### Codigo

1. Crear `signal_aggregator.py` con SignalAggregator
2. Modificar `poller.py`: guardar senales, llamar al aggregator en vez de BlockManager
3. Actualizar `capture.py`: instanciar SignalAggregator en vez de BlockManager
4. Anadir endpoints en `server.py`: signals, split, merge
5. Anadir metodos en `db.py`: create_signal, get_signals_by_date, get_signals_by_block
6. Actualizar frontend: tipo Signal, store, toggle en ReviewDayView, acciones split/merge
7. Anadir Tauri commands: get_signals, split_block, merge_blocks

## Configuracion

Nuevas opciones en Settings (General):

- **Umbral de inactividad**: minutos sin actividad para cerrar bloque (default: 5)
- **Apps navegador**: lista editable de apps que se tratan como navegadores
- **Apps transitorias**: lista editable de apps que no generan bloques propios

## Testing

### Tests del SignalAggregator

- Senales del mismo proyecto git → 1 bloque
- Senales de proyectos git diferentes → 2 bloques
- Senales de Chrome con dominios diferentes → bloques separados por dominio
- Gap de >5min → cierra bloque, abre nuevo
- Senal con app transitoria → hereda contexto anterior
- Bloqueo de pantalla → cierra bloque actual
- Crash recovery: retoma bloque auto reciente, cierra stale
- Bloque confirmado no se modifica por nuevas senales

### Tests de extraccion de dominio

- `"PR #42 — GitHub — Google Chrome"` → `"GitHub"`
- `"Inbox - Gmail — Google Chrome"` → `"Gmail"`
- `"Stack Overflow"` (sin browser suffix) → `"Stack Overflow"`
- Titulo vacio → fallback a app_name
- Titulo con separadores mixtos → extraccion correcta

### Tests de la API

- GET /signals?date=... devuelve senales del dia
- GET /signals?block_id=... devuelve senales de un bloque
- POST /blocks/{id}/split divide correctamente
- POST /blocks/merge fusiona correctamente
- No se puede partir/fusionar bloques confirmados

### Tests del frontend

- Toggle senales muestra/oculta la tabla
- Cada senal se asocia visualmente a su bloque
- Partir bloque actualiza la vista
- Fusionar bloques actualiza la vista
