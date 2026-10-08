#!/bin/bash
# PostToolUse hook: formatea con black y reporta flake8 tras editar un .py.
# Exit 2 -> stderr se muestra a Claude para que corrija/lo tenga en cuenta.
set -uo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-/Users/home/Developer/medicinedepot-odoo19-migration}"
VENV="$PROJECT_ROOT/.venv/bin"

input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')

[[ -z "$file_path" ]] && exit 0
[[ "$file_path" != *.py ]] && exit 0
[[ ! -f "$file_path" ]] && exit 0
[[ "$file_path" == *"/.venv/"* ]] && exit 0
[[ "$file_path" == *"/oca_addons/"* ]] && exit 0

report=""

black_output=$("$VENV/black" "$file_path" 2>&1)
if echo "$black_output" | grep -q "^reformatted"; then
  report+="black reformateó automáticamente $file_path (line-length 100).\n"
fi

flake8_output=$("$VENV/flake8" "$file_path" 2>&1)
if [[ -n "$flake8_output" ]]; then
  report+="flake8 encontró problemas en $file_path:\n$flake8_output\n"
fi

if [[ -n "$report" ]]; then
  printf '%b' "$report" >&2
  exit 2
fi

exit 0
