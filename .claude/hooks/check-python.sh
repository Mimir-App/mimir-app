#!/bin/bash
# Hook: PostToolUse Edit|Write — verifica archivos Python con pyright
# Recibe JSON por stdin con tool_input.file_path

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Solo archivos .py del daemon
if [[ "$FILE_PATH" == *.py ]] && [[ "$FILE_PATH" == *daemon* || "$FILE_PATH" == *mimir_daemon* ]]; then
    cd /opt/Mimir/mimir-app/daemon
    OUTPUT=$(.venv/bin/pyright "$FILE_PATH" 2>&1)
    EXIT_CODE=$?
    if [ $EXIT_CODE -ne 0 ]; then
        ERRORS=$(echo "$OUTPUT" | grep -c "error:")
        echo "{\"decision\": \"block\", \"reason\": \"pyright: $ERRORS errores en $FILE_PATH. Revisa los type errors antes de continuar.\"}"
        exit 0
    fi
fi
