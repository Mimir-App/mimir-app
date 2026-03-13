## Convenciones de codigo

### Python (daemon)
- Python 3.10+ minimo. Usar `asyncio` en todo el daemon; nada de threading salvo `pystray`
- Todas las clases y metodos publicos con **docstrings en espanol**
- **Type hints** completos en todas las funciones y metodos
- Todas las llamadas de red en async; UI updates solo via HTTP responses
- Todos los errores capturados — nunca crash; loggear errores, no tracebacks
- JSON guardado con `ensure_ascii=False`, UTF-8 en todo
- `logging` module a nivel INFO; loggear cada refresh, error y cambio de config
- Patron adaptador en todo: IA, integracion, notificaciones, fuentes externas
- Tokens OAuth NUNCA salen del ordenador local
- SQLite local: nunca queries sobre campos dentro de JSON blobs
- Todo codigo OS-specific va en `platform/`. Si aparece fuera, es un bug de arquitectura

### TypeScript / Vue (frontend)
- TypeScript strict mode
- Vue 3 con Composition API (`<script setup>`). No usar Options API
- Pinia: un store por dominio (`blocks`, `config`, `daemon`, `issues`, `merge_requests`, `timesheets`)
- Comunicacion con daemon via Tauri invoke commands (proxy HTTP en Rust)

### Rust (Tauri backend)
- Tauri 2 commands para proxy HTTP al daemon
- Keyring para almacenamiento seguro de tokens
- Config JSON local para preferencias de la app
- Modelos serde para serializar/deserializar

### General
- Considerar `BaseItemPanel` o composable compartido para logica comun Issues/MRs
- Tests: para cada adaptador, al menos un test con mock del servicio externo
- Distribucion: PyInstaller para el daemon, Tauri build para la app
