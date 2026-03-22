#!/bin/bash
# Hook: PostToolUse Edit|Write — verifica archivos TypeScript/Vue con vue-tsc
# Recibe JSON por stdin con tool_input.file_path

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Solo archivos .ts, .tsx, .vue del frontend
if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx || "$FILE_PATH" == *.vue ]]; then
    cd /opt/Mimir/mimir-app
    OUTPUT=$(npx vue-tsc --noEmit 2>&1)
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        ERRORS=$(echo "$OUTPUT" | grep -c "error TS")
        echo "{\"decision\": \"block\", \"reason\": \"vue-tsc: $ERRORS errores TypeScript. Revisa los type errors antes de continuar.\"}"
        exit 0
    fi
fi
