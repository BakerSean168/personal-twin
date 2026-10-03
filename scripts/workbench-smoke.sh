#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
viewer_url="${PERSONAL_TWIN_VIEWER_URL:-http://127.0.0.1:21024}"

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

# Verify the real browser archive, including embedded furniture models, can
# round-trip back into a desktop/MCP .sh3d home. An XML-only synthetic archive
# is not a valid substitute once the room contains embedded model resources.
docker compose -f "$repo_root/deploy/space-converter/compose.yaml" run --rm \
  converter \
  /data/bedroom.sh3x \
  /data/__smoke_web_roundtrip__.sh3d >/dev/null
python3 - "$repo_root/runtime/data/spaces/bedroom/__smoke_web_roundtrip__.sh3d" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as archive:
    home_xml = archive.read("Home.xml").decode("utf-8")
assert "pieceOfFurniture-b72f029a-d2d7-47b9-a88d-66dcf143d557" in home_xml
PY
rm -f "$repo_root/runtime/data/spaces/bedroom/__smoke_web_roundtrip__.sh3d"
printf 'OK furniture-rich browser .sh3x -> desktop/MCP .sh3d bridge\n'

for attempt in $(seq 1 20); do
  if curl -fsS --max-time 2 "$viewer_url/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
viewer_page="$(curl -fsS --max-time 10 "$viewer_url/")"
grep -Fq "Personal Twin Viewer" <<<"$viewer_page"
viewer_app="$(curl -fsS --max-time 10 "$viewer_url/app.js")"
grep -Fq "GLTFLoader" <<<"$viewer_app"
python3 - \
  "$repo_root/runtime/data/viewer/assets/manifest.json" \
  "$repo_root/runtime/data/ergonomics/seated-report.json" <<'PYVIEWER'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "room.glb",
    "room.json",
    "avatar-standing.glb",
    "avatar-standing.json",
    "body-summary.json",
    "room-integration.json",
    "scene-combined.glb",
    "scene-combined.json",
    "room-cutaway.glb",
    "scene-combined-cutaway.glb",
    "cutaway.json",
    "workstation-analysis.json",
}
assets = set(manifest.get("assets", {}))
missing = required - assets
assert not missing, missing
root = Path(sys.argv[1]).parent
for name in required:
    path = root / name
    assert path.is_file() and path.stat().st_size > 0, path

integration = json.loads((root / "room-integration.json").read_text(encoding="utf-8"))
combined = json.loads((root / "scene-combined.json").read_text(encoding="utf-8"))
seated = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
analysis = json.loads((root / "workstation-analysis.json").read_text(encoding="utf-8"))
cutaway = json.loads((root / "cutaway.json").read_text(encoding="utf-8"))

assert integration["validation"]["ok"] is True
assert cutaway["kind"] == "viewer-cutaway"
assert cutaway["presentationOnly"] is True
assert {"room-cutaway.glb", "scene-combined-cutaway.glb"} <= set(cutaway["outputs"])
for output in cutaway["outputs"].values():
    assert output["deletedFaces"] > 0
    assert output["frontWallFaces"] > 0
assert analysis["kind"] == "workstation-ergonomics-analysis"
assert analysis["summary"]["priorityFindingCount"] >= 0
assert analysis["checks"]["monitorViewingDistance"]["status"] in {"ok", "review"}
assert analysis["checks"]["monitorCenterDownAngle"]["status"] in {"ok", "review"}
assert analysis["checks"]["monitorTopRelativeToEye"]["status"] in {"ok", "review"}
assert abs(float(analysis["derived"]["monitorBottomAboveDesk_mm"]) - 215.0) <= 1.0
assert abs(float(analysis["derived"]["monitorTopAboveDesk_mm"]) - 575.0) <= 1.0
assert seated["poseVersion"] == "seated-v2-contact"
assert seated["constraints"]["canonicalSittingHeightEnforced"] is False
assert seated["validation"]["checks"]["seatContact"]["status"] == "ok"
assert seated["validation"]["checks"]["feet"]["status"] == "ok"
crown_delta = float(analysis["derived"]["crownMinusMonitorTop_mm"])
assert 40.0 <= crown_delta <= 70.0, crown_delta
monitor_finding = next(item for item in analysis["findings"] if item["id"] == "monitor-height")
assert monitor_finding["status"] == "review"
assert monitor_finding["suggestedAdjustment"]["action"] == "defer-monitor-adjustment"
assert monitor_finding["suggestedAdjustment"]["apply"] is False
assert len(analysis["references"]) >= 2
residuals = [
    *integration["validation"]["deskLocalResidual_mm"],
    *integration["validation"]["deskRoomResidual_mm"],
]
assert max(abs(float(value)) for value in residuals) <= integration["validation"]["tolerance_mm"]

body_min = combined["bodyBounds_m"]["min"]
body_max = combined["bodyBounds_m"]["max"]
assert abs(body_min[2] * 1000.0) <= 10.0, body_min
assert abs(body_max[2] * 1000.0 - seated["geometry"]["crownHeight_mm"]) <= 5.0, body_max
assert abs(
    (combined["bodyCenter_m"][0] - integration["stoolRoom_m"][0]) * 1000.0
) <= 1.0

print(
    f"OK Twin Viewer: {len(required)} required assets; "
    "integrated room/body transform validated"
)
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
assert scene["furnitureCount"] >= 3
furniture = {item["id"]: item for item in scene.get("furniture", [])}
for required_id in (
    "pieceOfFurniture-144ea215-ad2d-4ed0-b492-6f3e4fe9efdb",
    "pieceOfFurniture-2e7c7120-e11b-498c-a874-fb243aa757e8",
    "pieceOfFurniture-b72f029a-d2d7-47b9-a88d-66dcf143d557",
):
    assert required_id in furniture, required_id
monitor = furniture["pieceOfFurniture-b72f029a-d2d7-47b9-a88d-66dcf143d557"]
assert abs(float(monitor["elevation"]) - 98.5) <= 0.1
assert abs(float(monitor["height"]) - 36.0) <= 0.1
print(
    f'OK Sweet Home 3D MCP: {scene["wallCount"]} walls, '
    f'{scene["roomCount"]} room(s), {scene["furnitureCount"]} furniture/opening objects'
)

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
test -f "$repo_root/runtime/data/canonical/body/modeling.json"
test -f "$repo_root/runtime/data/body/body-measurements.json"
test -f "$repo_root/runtime/data/body/avatar-fit.json"
test -f "$repo_root/runtime/data/viewer/assets/room.glb"
test -f "$repo_root/runtime/data/viewer/assets/avatar-standing.glb"
test -f "$repo_root/runtime/data/ergonomics/avatar-seated.blend"
test -f "$repo_root/runtime/data/ergonomics/seated-report.json"

python3 "$repo_root/scripts/body/validate_modeling.py" \
  "$repo_root/runtime/data/canonical/body/modeling.json" >/dev/null
python3 - \
  "$repo_root/runtime/data/canonical/body/modeling.json" \
  "$repo_root/runtime/data/body/body-measurements.json" \
  "$repo_root/runtime/data/body/avatar-fit.json" <<'PYBODYFIT'
import json
import sys
from pathlib import Path

modeling = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
measurements = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
fit = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

assert measurements["validation"]["ok"] is True
assert fit["fitVersion"] == "body-v3-morphology-aware"
assert fit["measurementInfrastructureVersion"] == "body-morphology-fit-v3"
assert fit["measurementValidation"]["ok"] is True

configured = modeling["mpfb"]
after = fit["morphology"]["after"]
for name in ("gender", "cupsize", "firmness"):
    assert abs(float(after[name]) - float(configured[name])) <= 1e-6, (name, after[name], configured[name])

required_fits = {
    "height",
    "shoulderBreadth",
    "armLength",
    "footLength",
    "waistCircumference",
    "hipCircumference",
    "chestCircumference",
    "inseam",
}
assert required_fits <= set(fit["directlyFitted"])
print("OK Body V3 morphology + measurement fit")
PYBODYFIT

printf 'OK source assets present\n'

python3 "$repo_root/scripts/memory-smoke.py"
