#!/bin/bash
# Hook: PreToolUse Bash — bloquea git commit si los checks fallan
# Recibe JSON por stdin con tool_input.command

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Solo interceptar git commit
if [[ "$COMMAND" == *"git commit"* ]]; then
    ERRORS=""

    # 1. Tests Python
    cd /opt/Mimir/mimir-app/daemon
    PYTEST_OUT=$(.venv/bin/pytest tests/ -q 2>&1)
    if [ $? -ne 0 ]; then
        FAILED=$(echo "$PYTEST_OUT" | tail -1)
        ERRORS="$ERRORS\n- pytest: $FAILED"
    fi

    # 2. TypeScript check
    cd /opt/Mimir/mimir-app
    TSC_OUT=$(npx vue-tsc --noEmit 2>&1)
    if [ $? -ne 0 ]; then
        TSC_ERRORS=$(echo "$TSC_OUT" | grep -c "error TS")
        ERRORS="$ERRORS\n- vue-tsc: $TSC_ERRORS errores"
    fi

    # 3. Rust check
    cd /opt/Mimir/mimir-app/src-tauri
    CARGO_OUT=$(cargo check 2>&1)
    if [ $? -ne 0 ]; then
        ERRORS="$ERRORS\n- cargo check: fallo"
    fi

    if [ -n "$ERRORS" ]; then
        REASON=$(echo -e "Pre-commit checks fallaron:$ERRORS\nCorrige los errores antes de commitear.")
        echo "{\"hookSpecificOutput\": {\"hookEventName\": \"PreToolUse\", \"permissionDecision\": \"deny\", \"permissionDecisionReason\": \"$REASON\"}}"
        exit 0
    fi
fi
