Muestra el estado actual del proyecto Mimir. Ejecuta estos comandos y presenta un resumen:

1. **Version actual**: Lee la version de `package.json`
2. **Git status**: `git status --short`
3. **Branch actual**: `git branch --show-current`
4. **Ultimos 5 commits**: `git log --oneline -5`
5. **Tests daemon**: `cd daemon && .venv/bin/pytest tests/ -q 2>&1 | tail -3`
6. **Errores TypeScript**: `npx vue-tsc --noEmit 2>&1 | grep -c "error TS" || echo 0`

Formato de salida:

```
ESTADO DE MIMIR
---------------
Version:  vX.Y.Z
Branch:   <branch>
Estado:   <limpio | N archivos modificados>

Tests daemon: N/N pasando
TypeScript:   N errores
Rust:         (no verificado en status rapido)

Ultimos commits:
  <hash> <mensaje>
  ...
```
