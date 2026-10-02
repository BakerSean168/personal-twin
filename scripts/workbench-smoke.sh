#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

native_page="$(curl -fsS --max-time 10 http://127.0.0.1:21020/)"
grep -Fq "SweetHome3DJSApplication" <<<"$native_page"
homes="$(curl -fsS --max-time 10 http://127.0.0.1:21020/listHomes.php)"
python3 - "$homes" <<'PY'
import json
import sys
homes = json.loads(sys.argv[1])
assert "bedroom" in homes, homes
PY
unzip -l "$repo_root/runtime/data/spaces/bedroom/bedroom.sh3x" | grep -Fq "Home.xml"
printf 'OK native SweetHome3DJS editor\n'

# SweetHome3DJS may save XML-only .sh3x archives. Verify the bridge accepts
# that exact browser-side format and can turn it back into a desktop/MCP home.
python3 - "$repo_root/runtime/data/spaces/bedroom/bedroom.sh3x" \
           "$repo_root/runtime/data/spaces/bedroom/__smoke_web_only__.sh3x" <<'PY'
import sys
import zipfile
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
with zipfile.ZipFile(src) as archive:
    home_xml = archive.read("Home.xml")
with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("Home.xml", home_xml)
PY

docker compose -f "$repo_root/deploy/space-converter/compose.yaml" run --rm \
  converter \
  /data/__smoke_web_only__.sh3x \
  /data/__smoke_web_roundtrip__.sh3d >/dev/null
unzip -l "$repo_root/runtime/data/spaces/bedroom/__smoke_web_roundtrip__.sh3d" | grep -Fq "Home.xml"
rm -f \
  "$repo_root/runtime/data/spaces/bedroom/__smoke_web_only__.sh3x" \
  "$repo_root/runtime/data/spaces/bedroom/__smoke_web_roundtrip__.sh3d"
printf 'OK browser .sh3x -> desktop/MCP .sh3d bridge\n'

for attempt in $(seq 1 20); do
  if curl -fsS --max-time 2 http://127.0.0.1:21024/healthz >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
viewer_page="$(curl -fsS --max-time 10 http://127.0.0.1:21024/)"
grep -Fq "Personal Twin Viewer" <<<"$viewer_page"
viewer_app="$(curl -fsS --max-time 10 http://127.0.0.1:21024/app.js)"
grep -Fq "GLTFLoader" <<<"$viewer_app"
python3 - "$repo_root/runtime/data/viewer/assets/manifest.json" <<'PYVIEWER'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "room.glb",
    "room.json",
    "avatar-standing.glb",
    "avatar-standing.json",
    "avatar-seated.glb",
    "seated-v1-report.json",
    "body-summary.json",
}
assets = set(manifest.get("assets", {}))
missing = required - assets
assert not missing, missing
for name in required:
    path = Path(sys.argv[1]).parent / name
    assert path.is_file() and path.stat().st_size > 0, path
print(f"OK Twin Viewer: {len(required)} required assets")
PYVIEWER
"$repo_root/scripts/viewer/browser-smoke.sh"

curl -fsS --max-time 10 http://127.0.0.1:21029/ >/dev/null
printf 'OK maintenance Webtop\n'

tailnet_host=""
if command -v tailscale >/dev/null 2>&1; then
  tailnet_host="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))')"
fi
python3 - "$repo_root/runtime/data/mcp/servers.json" "$tailnet_host" <<'PY'
import json
import sys
from pathlib import Path

registry = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
tailnet_host = sys.argv[2]
expected = {
    "personal-twin-memory": ("streamable-http", "http://127.0.0.1:21023/mcp", 21023, "/mcp"),
    "sweet-home-3d": ("streamable-http", "http://127.0.0.1:21021/mcp", 21021, "/mcp"),
    "blender": ("sse", "http://127.0.0.1:21022/sse", 21022, "/sse"),
}
for name, (transport, local_url, port, suffix) in expected.items():
    entry = registry[name]
    assert entry["transport"] == transport
    assert entry["localUrl"] == local_url
    if tailnet_host:
        assert entry["tailnetUrl"] == f"https://{tailnet_host}:{port}{suffix}"
print(f"OK MCP registry: {len(expected)} services" + (" with tailnet URLs" if tailnet_host else ""))
PY

if [[ -n "$tailnet_host" ]]; then
  serve_status="$(tailscale serve status)"
  for port in 21020 21021 21022 21023 21024 21029; do
    grep -Fq "https://$tailnet_host:$port" <<<"$serve_status" || {
      printf 'Missing Tailscale Serve endpoint for port %s\n' "$port" >&2
      exit 1
    }
  done
  printf 'OK Tailscale Serve: native editor + Twin Viewer + Webtop + 3 MCP endpoints\n'
fi

python3 - <<'PY'
import json
import os
import urllib.request

base = os.environ.get("PERSONAL_TWIN_SH3D_MCP_URL", "http://127.0.0.1:21021/mcp")

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

def call_tool(sid, request_id, name, arguments):
    _, response = post({
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }, sid)
    if "error" in response:
        raise RuntimeError(response["error"])
    result = response["result"]
    if result.get("isError"):
        raise RuntimeError(result)
    return json.loads(result["content"][0]["text"])

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
scene = call_tool(sid, 2, "get_state", {})
assert scene["wallCount"] >= 4
assert scene["roomCount"] >= 1
print(f'OK Sweet Home 3D MCP: {scene["wallCount"]} walls, {scene["roomCount"]} room(s)')

marker = "__personal_twin_write_smoke__"
checkpoint = call_tool(sid, 3, "checkpoint", {"description": "Personal Twin reversible write smoke"})
try:
    call_tool(sid, 4, "add_label", {"text": marker, "x": 0, "y": 0})
    changed = call_tool(sid, 5, "get_state", {})
    assert any(label.get("text") == marker for label in changed.get("labels", []))
finally:
    call_tool(sid, 6, "restore_checkpoint", {"id": checkpoint["id"], "force": True})
restored = call_tool(sid, 7, "get_state", {})
assert not any(label.get("text") == marker for label in restored.get("labels", []))
print("OK Sweet Home 3D MCP reversible write")
PY

workbench_container="$(docker compose -f "$repo_root/deploy/workbench/compose.yaml" ps -q workbench)"
if [[ -z "$workbench_container" ]]; then
  printf 'Personal Twin workbench container is not running\n' >&2
  exit 1
fi

docker exec -i "$workbench_container" /opt/personal-twin/mcp-venv/bin/python - <<'PY'
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    async with sse_client("http://127.0.0.1:9878/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            marker = "__PersonalTwinWriteSmoke__"
            create = await session.call_tool(
                "execute_blender_code",
                {
                    "code": (
                        "import bpy\n"
                        f"name = {marker!r}\n"
                        "old = bpy.data.objects.get(name)\n"
                        "if old is not None: bpy.data.objects.remove(old, do_unlink=True)\n"
                        "obj = bpy.data.objects.new(name, None)\n"
                        "bpy.context.scene.collection.objects.link(obj)\n"
                        "result = {'created': bpy.data.objects.get(name) is not None}\n"
                    )
                },
            )
            assert not create.isError
            result = await session.call_tool("get_objects_summary", {})
            data = result.structuredContent or {}
            scene = data.get("result", {})
            def collect_objects(collection):
                objects = list(collection.get("objects", []))
                for child in collection.get("children", []):
                    objects.extend(collect_objects(child))
                return objects

            objects = []
            for collection in scene.get("collections", []):
                objects.extend(collect_objects(collection))
            names = [obj.get("name") for obj in objects]
            assert "PersonalTwinAvatar" in names
            assert marker in names

            removed = await session.call_tool(
                "execute_blender_code",
                {
                    "code": (
                        "import bpy\n"
                        f"name = {marker!r}\n"
                        "obj = bpy.data.objects.get(name)\n"
                        "if obj is not None: bpy.data.objects.remove(obj, do_unlink=True)\n"
                        "result = {'removed': bpy.data.objects.get(name) is None}\n"
                    )
                },
            )
            assert not removed.isError
            result = await session.call_tool("get_objects_summary", {})
            data = result.structuredContent or {}
            scene = data.get("result", {})
            objects = []
            for collection in scene.get("collections", []):
                objects.extend(collect_objects(collection))
            names = [obj.get("name") for obj in objects]
            assert marker not in names
            assert "PersonalTwinAvatar" in names
            print(f"OK Blender MCP reversible write; objects={names}")

asyncio.run(main())
PY

test -f "$repo_root/runtime/data/spaces/bedroom/bedroom.sh3d"
test -f "$repo_root/runtime/data/spaces/bedroom/bedroom.sh3x"
test -f "$repo_root/runtime/data/body/avatar.blend"
test -f "$repo_root/runtime/data/viewer/assets/room.glb"
test -f "$repo_root/runtime/data/viewer/assets/avatar-standing.glb"
test -f "$repo_root/runtime/data/viewer/assets/avatar-seated.glb"
printf 'OK source assets present\n'

python3 "$repo_root/scripts/memory-smoke.py"
