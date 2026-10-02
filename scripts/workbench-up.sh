#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime="$repo_root/runtime"
data_root="$runtime/data"
config_root="$runtime/workbench/config"

mkdir -p "$data_root"/{body,spaces/bedroom,exports,canonical/spaces/bedroom,canonical/body,mcp} "$config_root"

legacy_room="$repo_root/data/private/spaces/bedroom/room.json"
canonical_room="$data_root/canonical/spaces/bedroom/room.json"
if [[ -f "$legacy_room" && ! -f "$canonical_room" ]]; then
  cp "$legacy_room" "$canonical_room"
fi

# The converter reuses Sweet Home 3D from the workbench image, so build that
# image first. Stop both human and AI editors before reconciling the two file
# formats to prevent a concurrent save from racing with startup.
docker compose -f "$repo_root/deploy/workbench/compose.yaml" build
docker compose -f "$repo_root/deploy/space-converter/compose.yaml" build
"$repo_root/scripts/fetch-space-web.sh"

docker compose -f "$repo_root/deploy/space-web/compose.yaml" stop >/dev/null 2>&1 || true
docker compose -f "$repo_root/deploy/workbench/compose.yaml" stop >/dev/null 2>&1 || true

"$repo_root/scripts/space-reconcile.sh"

docker compose -f "$repo_root/deploy/workbench/compose.yaml" up -d --force-recreate --no-build
docker compose -f "$repo_root/deploy/space-web/compose.yaml" up -d --build

"$repo_root/scripts/viewer/build-assets.sh"
docker compose -f "$repo_root/deploy/twin-viewer/compose.yaml" up -d --build

tailnet_host=""
if command -v tailscale >/dev/null 2>&1; then
  tailscale serve --bg --yes --https=21020 http://127.0.0.1:21020
  tailscale serve --bg --yes --https=21021 http://127.0.0.1:21021
  tailscale serve --bg --yes --https=21022 http://127.0.0.1:21022
  tailscale serve --bg --yes --https=21023 http://127.0.0.1:21023
  tailscale serve --bg --yes --https=21024 http://127.0.0.1:21024
  tailscale serve --bg --yes --https=21029 http://127.0.0.1:21029
  tailnet_host="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))')"
fi

python3 "$repo_root/scripts/render-mcp-registry.py" "$data_root/mcp/servers.json" "$tailnet_host"

printf 'Personal Twin Workbench started.\n'
if [[ -n "$tailnet_host" ]]; then
  printf 'Space Web:   https://%s:21020\n' "$tailnet_host"
  printf 'Sweet Home:  https://%s:21021/mcp\n' "$tailnet_host"
  printf 'Blender MCP: https://%s:21022/sse\n' "$tailnet_host"
  printf 'Memory MCP:  https://%s:21023/mcp\n' "$tailnet_host"
  printf 'Twin Viewer: https://%s:21024\n' "$tailnet_host"
  printf 'Webtop:      https://%s:21029\n' "$tailnet_host"
fi
