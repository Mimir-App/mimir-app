Ejecuta la suite completa de verificacion del proyecto Mimir:

1. **Tests Python (daemon)**:
   ```bash
   cd daemon && source .venv/bin/activate && pytest tests/ -v
   ```

2. **TypeScript check (frontend)**:
   ```bash
   npx vue-tsc --noEmit
   ```

3. **Rust check (Tauri backend)**:
   ```bash
   cd src-tauri && cargo check
   ```

Ejecuta los tres en orden. Reporta un resumen al final con formato:

```
VERIFICACION COMPLETA
---------------------
pytest:    OK (N tests) | FALLO (N fallos)
vue-tsc:   OK (0 errores) | FALLO (N errores)
cargo:     OK | FALLO
```

Si hay fallos, lista los errores especificos para que se puedan corregir.
