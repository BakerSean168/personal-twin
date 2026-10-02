#!/usr/bin/env python3
from __future__ import annotations

import bmesh
import bpy
import json
from mathutils import Matrix, Vector
from pathlib import Path

ROOM = "/data/viewer/assets/room.glb"
SEATED_BLEND = "/data/ergonomics/avatar-seated.blend"
TRANSFORM = "/data/viewer/assets/room-integration.json"
OUT = "/data/viewer/assets/scene-combined.glb"
META = "/data/viewer/assets/scene-combined.json"

with open(TRANSFORM, "r", encoding="utf-8") as handle:
    integration = json.load(handle)

matrix = Matrix(integration["matrixRowMajor"])
if matrix.to_3x3().determinant() >= 0:
    raise RuntimeError("expected handedness-changing ergonomics-to-room transform")

body = bpy.data.objects.get("PersonalTwinAvatar")
if body is None or body.type != "MESH":
    raise RuntimeError("seated Blender scene is missing PersonalTwinAvatar")

# Bake the already-validated seated pose before removing its rig/environment.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(depsgraph)
mesh = bpy.data.meshes.new_from_object(
    evaluated,
    preserve_all_data_layers=True,
    depsgraph=depsgraph,
)
static_body = bpy.data.objects.new("PersonalTwinAvatar.RoomIntegrated", mesh)
bpy.context.scene.collection.objects.link(static_body)
static_body.matrix_world = body.matrix_world.copy()

# Remove all seated-scene source objects (rig, pose targets and proxy furniture).
for obj in list(bpy.context.scene.objects):
    if obj != static_body:
        bpy.data.objects.remove(obj, do_unlink=True)

# Bake the posed body into normalized room-viewer coordinates. The Y flip is a
# coordinate-system conversion; reverse winding so normals remain outward.
for vertex in static_body.data.vertices:
    local_world = static_body.matrix_world @ vertex.co
    vertex.co = matrix @ local_world
static_body.matrix_world = Matrix.Identity(4)

bm = bmesh.new()
bm.from_mesh(static_body.data)
bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
bm.to_mesh(static_body.data)
bm.free()
static_body.data.update()

mins = Vector((1e18, 1e18, 1e18))
maxs = Vector((-1e18, -1e18, -1e18))
for vertex in static_body.data.vertices:
    point = static_body.matrix_world @ vertex.co
    for axis in range(3):
        mins[axis] = min(mins[axis], point[axis])
        maxs[axis] = max(maxs[axis], point[axis])

# Import the actual room only after the body is baked and proxy furniture is gone.
bpy.ops.import_scene.gltf(filepath=ROOM)
room_objects = [
    obj for obj in bpy.context.scene.objects if obj != static_body
]
if not room_objects:
    raise RuntimeError("room GLB imported no objects")

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=False,
    export_apply=True,
)

payload = {
    "schemaVersion": 1,
    "kind": "integrated-room-seated-body",
    "room": ROOM,
    "bodySource": SEATED_BLEND,
    "transform": TRANSFORM,
    "bodyObject": static_body.name,
    "bodyBounds_m": {"min": list(mins), "max": list(maxs)},
    "bodyCenter_m": list((mins + maxs) / 2),
    "roomObjectCount": len(room_objects),
}
Path(META).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("PERSONAL_TWIN_COMBINED=" + json.dumps(payload, separators=(",", ":")))
