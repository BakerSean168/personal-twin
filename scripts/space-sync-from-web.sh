#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
room_dir="$repo_root/runtime/data/spaces/bedroom"
web_file="$room_dir/bedroom.sh3x"
desktop_file="$room_dir/bedroom.sh3d"
next_file="$room_dir/bedroom.sh3d.next"

if [[ ! -f "$web_file" ]]; then
  echo "missing web room: $web_file" >&2
  exit 1
fi

if [[ -f "$desktop_file" && ! "$web_file" -nt "$desktop_file" ]]; then
  echo "desktop/MCP room is already current"
  exit 0
fi

rm -f "$next_file"
docker compose -f "$repo_root/deploy/space-converter/compose.yaml" run --rm   converter   /data/bedroom.sh3x   /data/bedroom.sh3d.next >/dev/null
mv -f "$next_file" "$desktop_file"

python3 - <<'PY'
import json
import urllib.request

base = "http://127.0.0.1:21021/mcp"

def post(payload, sid=None):
    request = urllib.request.Request(
        base,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    if sid:
        request.add_header("Mcp-Session-Id", sid)
    with urllib.request.urlopen(request, timeout=15) as response:
        raw = response.read()
        return response.headers, json.loads(raw) if raw else None

headers, _ = post({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "personal-twin-space-sync", "version": "1"},
    },
})
sid = headers.get("Mcp-Session-Id")
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, sid)
_, result = post({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "load_home",
        "arguments": {"filePath": "/data/spaces/bedroom/bedroom.sh3d"},
    },
}, sid)
if result.get("error"):
    raise SystemExit(result["error"])
tool_result = result.get("result", {})
if tool_result.get("isError"):
    raise SystemExit(tool_result)
PY

echo "synced web room -> desktop/MCP room and reloaded it"
