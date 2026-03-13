Lee el archivo `.claude/agents/reviewer.md` para conocer el rol y el proceso de revision.

Usa el Agent tool para despachar un subagente de tipo `general-purpose` con el siguiente prompt:

"Actua segun las instrucciones de `.claude/agents/reviewer.md`. Revisa el codigo del proyecto Mimir $ARGUMENTS. El directorio raiz del proyecto es el directorio de trabajo actual. Si se especifica una fase, revisa solo los archivos de esa fase. Si no se especifica, revisa todo el codigo implementado hasta el momento."
