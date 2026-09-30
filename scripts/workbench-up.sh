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

docker compose -f "$repo_root/deploy/workbench/compose.yaml" up -d --build

if command -v tailscale >/dev/null 2>&1; then
  tailscale serve --bg --yes --https=21020 http://127.0.0.1:21020
  tailscale serve --bg --yes --https=21021 http://127.0.0.1:21021
  tailscale serve --bg --yes --https=21022 http://127.0.0.1:21022
fi

printf 'Personal Twin Workbench started.\n'
if command -v tailscale >/dev/null 2>&1; then
  tailnet_host="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))')"
  if [[ -n "$tailnet_host" ]]; then
    printf 'Web:         https://%s:21020\n' "$tailnet_host"
    printf 'Sweet Home:  https://%s:21021/mcp\n' "$tailnet_host"
    printf 'Blender MCP: https://%s:21022/sse\n' "$tailnet_host"
  fi
fi
