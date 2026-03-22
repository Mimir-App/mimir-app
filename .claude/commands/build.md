Ejecuta el script de build de Mimir con el target especificado.

Si se proporcionan argumentos ($ARGUMENTS), usalos como target:
```bash
bash scripts/build.sh $ARGUMENTS
```

Targets disponibles:
- `capture` — Solo capture daemon
- `server` — Solo server daemon
- `daemon` — Ambos + instalador
- `app` — Solo app Tauri
- `deb` — Paquetes .deb unificados
- (sin argumento) — Todo

Reporta el resultado del build y cualquier error encontrado.
