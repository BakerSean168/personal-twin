#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
container="$(docker compose -f "$repo_root/deploy/workbench/compose.yaml" ps -q workbench)"

if [[ -z "$container" ]]; then
  printf 'Personal Twin workbench is not running\n' >&2
  exit 1
fi

standing_script="/tmp/personal-twin-export-standing.py"
room_script="/tmp/personal-twin-convert-room.py"
combined_script="/tmp/personal-twin-build-combined.py"

docker cp \
  "$repo_root/scripts/viewer/export_standing_blender.py" \
  "$container:$standing_script" >/dev/null

docker cp \
  "$repo_root/scripts/viewer/convert_room_blender.py" \
  "$container:$room_script" >/dev/null

docker cp \
  "$repo_root/scripts/integration/build_combined_blender.py" \
  "$container:$combined_script" >/dev/null

mkdir -p "$repo_root/runtime/data/viewer/assets"

docker exec "$container" \
  /opt/blender/blender \
  --background /data/body/avatar.blend \
  --python "$standing_script"

if [[ -f "$repo_root/runtime/data/viewer/source/room-obj/export.obj" ]]; then
  docker exec "$container" \
    /opt/blender/blender \
    --background \
    --python "$room_script"
else
  printf 'WARN room OBJ source missing; room.glb not rebuilt\n' >&2
fi

if [[ -f "$repo_root/runtime/data/ergonomics/avatar-seated.glb" ]]; then
  cp -f \
    "$repo_root/runtime/data/ergonomics/avatar-seated.glb" \
    "$repo_root/runtime/data/viewer/assets/avatar-seated.glb"
fi

if [[ -f "$repo_root/runtime/data/ergonomics/seated-v1-report.json" ]]; then
  cp -f \
    "$repo_root/runtime/data/ergonomics/seated-v1-report.json" \
    "$repo_root/runtime/data/viewer/assets/seated-v1-report.json"
fi

python3 - \
  "$repo_root/runtime/data/canonical/body/profile.json" \
  "$repo_root/runtime/data/viewer/assets/body-summary.json" <<'PYBODY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])

if source.is_file():
    profile = json.loads(source.read_text(encoding="utf-8"))
    measurements = profile.get("measurements", {})
    selected = {}
    for name in ("height", "weight", "shoulderBreadth"):
        item = measurements.get(name)
        if isinstance(item, dict) and item.get("value") is not None and item.get("unit"):
            selected[name] = {"value": item["value"], "unit": item["unit"]}

    target.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "profileId": profile.get("profileId"),
                "measurements": selected,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
PYBODY

integration_inputs=(
  "$repo_root/runtime/data/viewer/assets/room.json"
  "$repo_root/runtime/data/canonical/ergonomics/desk-setup.json"
  "$repo_root/runtime/data/canonical/ergonomics/room-anchor.json"
  "$repo_root/runtime/data/ergonomics/avatar-seated.blend"
)

integration_ready=true
for path in "${integration_inputs[@]}"; do
  if [[ ! -f "$path" ]]; then
    integration_ready=false
    printf 'WARN integrated scene input missing: %s\n' "$path" >&2
  fi
done

if [[ "$integration_ready" == true ]]; then
  python3 "$repo_root/scripts/integration/build_room_transform.py" >/dev/null
  docker exec "$container" \
    /opt/blender/blender \
    --background /data/ergonomics/avatar-seated.blend \
    --python "$combined_script"
else
  printf 'WARN integrated room/body scene not rebuilt\n' >&2
fi

python3 - "$repo_root/runtime/data/viewer/assets" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
assets = {}
for name in (
    "room.glb",
    "room.json",
    "avatar-standing.glb",
    "avatar-standing.json",
    "avatar-seated.glb",
    "seated-v1-report.json",
    "body-summary.json",
    "room-integration.json",
    "scene-combined.glb",
    "scene-combined.json",
):
    path = root / name
    if not path.is_file():
        continue
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assets[name] = {"sizeBytes": path.stat().st_size, "sha256": digest}

(root / "manifest.json").write_text(
    json.dumps({"schemaVersion": 1, "assets": assets}, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps({"assets": sorted(assets)}, ensure_ascii=False))
PY
