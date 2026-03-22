Verificacion rapida del proyecto Mimir (sin tests, solo type checking):

1. **TypeScript**:
   ```bash
   npx vue-tsc --noEmit
   ```

2. **Rust**:
   ```bash
   cd src-tauri && cargo check
   ```

Reporta resultado con formato:

```
CHECK RAPIDO
------------
vue-tsc: OK | FALLO (N errores)
cargo:   OK | FALLO
```
