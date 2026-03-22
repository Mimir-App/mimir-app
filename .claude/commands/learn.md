Extrae patrones reutilizables de la sesion actual y evalualos antes de guardar.

## Proceso

1. **Revisa la sesion**: analiza los cambios hechos (git diff, archivos tocados, decisiones tomadas)
2. **Identifica patrones**: busca:
   - Resoluciones de errores no triviales (root cause + fix)
   - Tecnicas de debugging utiles
   - Workarounds de librerias o APIs
   - Decisiones de arquitectura o convenciones del proyecto
   - Patrones de codigo que se repitieron
3. **Evalua calidad**: para cada patron pregunta:
   - Es reutilizable en futuras sesiones? (no guardar fixes triviales)
   - Ya existe en memoria o en `.claude/context/`? (no duplicar)
   - Es especifico del proyecto o generico?
4. **Decide donde guardar**:
   - Si es una convencion o patron de Mimir → actualizar `.claude/context/conventions.md` o `.claude/context/architecture.md`
   - Si es feedback sobre como trabajar → guardar en memoria como tipo `feedback`
   - Si es contexto del proyecto → guardar en memoria como tipo `project`
   - Si no aporta valor → descartarlo y explicar por que
5. **Presenta el resultado**: muestra que se extrajo, donde se guardo, y que se descarto

## Reglas

- No extraer fixes triviales (typos, imports faltantes)
- No duplicar lo que ya existe en los archivos de contexto
- Un patron por entrada — si hay varios, guardar cada uno por separado
- Incluir **Why** y **How to apply** en memorias de tipo feedback/project
- Si no hay nada valioso que extraer, decirlo directamente
