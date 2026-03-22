#!/usr/bin/env bash
# Stop hook: recuerda al usuario hacer commit si hay cambios pendientes
cd "$CLAUDE_PROJECT_DIR" || exit 0

changes=$(git diff --name-only HEAD 2>/dev/null)
untracked=$(git ls-files --others --exclude-standard 2>/dev/null)

if [ -n "$changes" ] || [ -n "$untracked" ]; then
  # Construir mensaje de resumen
  msg="Recuerda hacer commit. Archivos modificados:"
  if [ -n "$changes" ]; then
    msg="$msg\n  Modificados: $(echo "$changes" | wc -l | tr -d ' ')"
  fi
  if [ -n "$untracked" ]; then
    msg="$msg\n  Sin trackear: $(echo "$untracked" | wc -l | tr -d ' ')"
  fi
  echo -e "$msg"
fi
