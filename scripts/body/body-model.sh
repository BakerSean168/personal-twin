#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
action="measure"
if [[ $# -gt 0 ]]; then
  action="$1"
fi

case "$action" in
  measure|fit|validate) ;;
  *)
    printf 'Usage: %s {measure|fit|validate}\n' "$0" >&2
    exit 2
    ;;
esac

container="$(docker compose -f "$repo_root/deploy/workbench/compose.yaml" ps -q workbench)"
if [[ -z "$container" ]]; then
  printf 'Personal Twin workbench is not running\n' >&2
  exit 1
fi

docker exec -i "$container" /opt/personal-twin/mcp-venv/bin/python - "$action"   < "$repo_root/scripts/body/body_model.py"
