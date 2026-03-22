Ayuda a convertir una idea en un diseno concreto mediante dialogo colaborativo.

## Argumento

$ARGUMENTS — descripcion de la idea o feature a explorar. Si esta vacio, pregunta al usuario que quiere disenar.

## Proceso

1. **Explora contexto**: lee los archivos relevantes del proyecto (CLAUDE.md, architecture.md, conventions.md, codigo existente relacionado)
2. **Pregunta para clarificar**: una pregunta a la vez, preferiblemente multiple choice. Enfocate en:
   - Proposito y motivacion
   - Restricciones y dependencias
   - Criterios de exito
3. **Propone 2-3 enfoques**: con trade-offs claros y tu recomendacion
4. **Presenta el diseno**: seccion por seccion, pidiendo OK tras cada una:
   - Arquitectura y componentes
   - Flujo de datos
   - Cambios en DB/API/UI
   - Testing
5. **Documenta**: guarda el diseno en `.claude/plans/` como `YYYY-MM-DD-<tema>.md`
6. **Revisa**: lee el spec y verifica coherencia interna antes de presentarlo al usuario

## Principios

- **Una pregunta a la vez** — no abrumar
- **YAGNI** — eliminar features innecesarias del diseno
- **Explorar alternativas** — siempre 2-3 opciones antes de decidir
- **Validacion incremental** — aprobacion por secciones
- **Seguir patrones existentes** — respetar conventions.md y architecture.md
- **Escala proporcional** — un fix simple necesita un parrafo, no un documento de 5 paginas
