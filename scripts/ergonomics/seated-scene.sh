#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
action="build"
if [[ $# -gt 0 ]]; then
  action="$1"
fi

case "$action" in
  build|validate) ;;
  *)
    printf 'Usage: %s {build|validate}\n' "$0" >&2
    exit 2
    ;;
esac

python3 "$repo_root/scripts/ergonomics/validate_setup.py" "$repo_root/runtime/data/canonical/ergonomics/desk-setup.json" >/dev/null

container="$(docker compose -f "$repo_root/deploy/workbench/compose.yaml" ps -q workbench)"
if [[ -z "$container" ]]; then
  printf 'Personal Twin workbench is not running\n' >&2
  exit 1
fi

script_in_container="/tmp/personal-twin-seated-blender.py"
docker cp "$repo_root/scripts/ergonomics/seated_blender.py" "$container:$script_in_container" >/dev/null

if [[ "$action" == "build" ]]; then
  input="/data/body/avatar.blend"
else
  input="/data/ergonomics/avatar-seated.blend"
fi

docker exec "$container" /opt/blender/blender   --background "$input"   --python "$script_in_container"   -- --action "$action"
