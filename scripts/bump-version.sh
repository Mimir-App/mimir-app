#!/usr/bin/env bash
# bump-version.sh — Actualiza la version en todos los archivos del proyecto.
#
# Uso:
#   bash scripts/bump-version.sh patch|minor|major
#   bash scripts/bump-version.sh 0.5.0          # version explicita
#
# Archivos actualizados:
#   - package.json
#   - src-tauri/tauri.conf.json
#   - src-tauri/Cargo.toml
#   - daemon/pyproject.toml

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# --- Leer version actual ---
CURRENT=$(python3 -c "import json; print(json.load(open('$ROOT/package.json'))['version'])")
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# --- Calcular nueva version ---
case "${1:-}" in
  patch) PATCH=$((PATCH + 1)) ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  [0-9]*.*)
    IFS='.' read -r MAJOR MINOR PATCH <<< "$1"
    ;;
  *)
    echo "Uso: $0 patch|minor|major|X.Y.Z"
    exit 1
    ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"

if [ "$NEW" = "$CURRENT" ]; then
  echo "La version ya es $CURRENT"
  exit 0
fi

echo "Bumping: $CURRENT -> $NEW"

# --- package.json ---
python3 -c "
import json, pathlib
p = pathlib.Path('$ROOT/package.json')
d = json.loads(p.read_text())
d['version'] = '$NEW'
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
"

# --- tauri.conf.json ---
python3 -c "
import json, pathlib
p = pathlib.Path('$ROOT/src-tauri/tauri.conf.json')
d = json.loads(p.read_text())
d['version'] = '$NEW'
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
"

# --- Cargo.toml (solo la linea version del [package]) ---
sed -i "0,/^version = \".*\"/s//version = \"$NEW\"/" "$ROOT/src-tauri/Cargo.toml"

# --- pyproject.toml ---
sed -i "s/^version = \".*\"/version = \"$NEW\"/" "$ROOT/daemon/pyproject.toml"

echo "Version actualizada a $NEW en:"
echo "  - package.json"
echo "  - src-tauri/tauri.conf.json"
echo "  - src-tauri/Cargo.toml"
echo "  - daemon/pyproject.toml"
