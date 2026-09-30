#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

curl -fsS --max-time 10 http://127.0.0.1:21020/ >/dev/null
printf 'OK web workbench\n'

python3 - <<'PY'
import json
import urllib.request

base = "http://127.0.0.1:21021/mcp"

def post(payload, sid=None):
    req = urllib.request.Request(
        base,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    if sid:
        req.add_header("Mcp-Session-Id", sid)
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        return resp.headers, json.loads(raw) if raw else None

headers, _ = post({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "personal-twin-smoke", "version": "1.0"},
    },
})
sid = headers.get("Mcp-Session-Id")
post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, sid)
_, state = post({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {"name": "get_state", "arguments": {}},
}, sid)
content = state["result"]["content"][0]["text"]
scene = json.loads(content)
assert scene["wallCount"] >= 4
assert scene["roomCount"] >= 1
print(f'OK Sweet Home 3D MCP: {scene["wallCount"]} walls, {scene["roomCount"]} room(s)')
PY

docker exec -i personal-twin-workbench /opt/personal-twin/mcp-venv/bin/python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://127.0.0.1:9878/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_objects_summary", {})
            data = result.structuredContent or {}
            scene = data.get("result", {})
            objects = []
            for collection in scene.get("collections", []):
                for child in collection.get("children", []):
                    objects.extend(child.get("objects", []))
            names = [obj.get("name") for obj in objects]
            assert "PersonalTwinAvatar" in names
            print(f"OK Blender MCP: objects={names}")

asyncio.run(main())
PY

test -f "$repo_root/runtime/data/spaces/bedroom/bedroom.sh3d"
test -f "$repo_root/runtime/data/body/avatar.blend"
printf 'OK source assets present\n'
