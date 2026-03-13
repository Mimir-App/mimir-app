Lee el archivo `.claude/agents/verifier.md` para conocer el rol y el proceso de verificacion.

Usa el Agent tool para despachar un subagente de tipo `general-purpose` con el siguiente prompt:

"Actua segun las instrucciones de `.claude/agents/verifier.md`. Verifica que la FASE $ARGUMENTS del proyecto Mimir esta correctamente implementada. El directorio raiz del proyecto es el directorio de trabajo actual. Genera el reporte completo segun el formato definido en el agente."
