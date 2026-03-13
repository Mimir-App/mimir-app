Lee el archivo `.claude/agents/implementor.md` para conocer el rol y las reglas del agente implementador.

Usa el Agent tool para despachar un subagente de tipo `general-purpose` con el siguiente prompt:

"Actua estrictamente segun las instrucciones de `.claude/agents/implementor.md`. Tu tarea es implementar la FASE $ARGUMENTS del proyecto Mimir. El directorio raiz del proyecto es el directorio de trabajo actual. Lee primero el plan completo en `.claude/plans/IMPLEMENTATION_PLAN.md` antes de escribir ningun archivo."
