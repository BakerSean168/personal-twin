#!/usr/bin/env python3
import bpy
import json
from mathutils import Vector
from pathlib import Path

OBJ = "/data/viewer/source/room-obj/export.obj"
OUT = "/data/viewer/assets/room.glb"
MANIFEST = "/data/viewer/assets/room.json"

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=OBJ)

meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
if not meshes:
    raise RuntimeError("room OBJ imported no mesh objects")

# Sweet Home 3D OBJ coordinates are centimeters with Z-up. Convert to meters.
for obj in meshes:
    obj.scale = (0.01, 0.01, 0.01)
bpy.context.view_layer.update()

mins = Vector((1e18, 1e18, 1e18))
maxs = Vector((-1e18, -1e18, -1e18))
for obj in meshes:
    for corner in obj.bound_box:
        point = obj.matrix_world @ Vector(corner)
        for axis in range(3):
            mins[axis] = min(mins[axis], point[axis])
            maxs[axis] = max(maxs[axis], point[axis])

# Normalize for standalone web viewing: center plan footprint at origin and put floor at Z=0.
center = (mins + maxs) / 2
offset = Vector((-center.x, -center.y, -mins.z))
for obj in meshes:
    obj.location += offset
bpy.context.view_layer.update()

normalized_min = mins + offset
normalized_max = maxs + offset

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=False,
    export_apply=True,
)

payload = {
    "schemaVersion": 1,
    "kind": "room",
    "source": "/data/viewer/source/room-obj/export.obj",
    "sourceUnit": "cm",
    "outputUnit": "m",
    "sourceAxes": {
        "x": "sweet-home-3d-plan-right",
        "y": "negative-sweet-home-3d-plan-down",
        "z": "up",
    },
    "normalizationOffset_m": list(offset),
    "sourceBounds": {"min": list(mins), "max": list(maxs)},
    "normalizedBounds": {"min": list(normalized_min), "max": list(normalized_max)},
    "dimensions_m": list(normalized_max - normalized_min),
    "objectCount": len(meshes),
}
Path(MANIFEST).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("PERSONAL_TWIN_ROOM=" + json.dumps(payload, separators=(",", ":")))
