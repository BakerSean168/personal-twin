#!/usr/bin/env python3
import bpy
import json
from mathutils import Vector
from pathlib import Path

OUT = "/data/viewer/assets/avatar-standing.glb"
MANIFEST = "/data/viewer/assets/avatar-standing.json"

body = bpy.data.objects.get("PersonalTwinAvatar")
if body is None or body.type != "MESH":
    raise RuntimeError("PersonalTwinAvatar mesh is missing")


def world_bounds(obj):
    minimum = Vector((1e18, 1e18, 1e18))
    maximum = Vector((-1e18, -1e18, -1e18))
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        for axis in range(3):
            minimum[axis] = min(minimum[axis], point[axis])
            maximum[axis] = max(maximum[axis], point[axis])
    return minimum, maximum


# The editable Blender source keeps MPFB shape keys. The Web Viewer only needs
# the resolved body surface, so export a static evaluated mesh. This removes
# morph-target/runtime compatibility from the presentation layer.
depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = body.evaluated_get(depsgraph)
mesh = bpy.data.meshes.new_from_object(
    evaluated,
    preserve_all_data_layers=True,
    depsgraph=depsgraph,
)
static_body = bpy.data.objects.new("PersonalTwinAvatar.ViewerStanding", mesh)
bpy.context.scene.collection.objects.link(static_body)
static_body.matrix_world = body.matrix_world.copy()

source_min, source_max = world_bounds(static_body)
floor_offset = -source_min.z
static_body.location.z += floor_offset
bpy.context.view_layer.update()
normalized_min, normalized_max = world_bounds(static_body)

for obj in bpy.context.scene.objects:
    obj.select_set(False)
static_body.select_set(True)
bpy.context.view_layer.objects.active = static_body

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=True,
)

payload = {
    "schemaVersion": 2,
    "kind": "standing-avatar",
    "representation": "static-evaluated-mesh",
    "source": "/data/body/avatar.blend",
    "sourceObject": body.name,
    "object": static_body.name,
    "sourceBounds_m": {"min": list(source_min), "max": list(source_max)},
    "normalizedBounds_m": {"min": list(normalized_min), "max": list(normalized_max)},
    "dimensions_m": list(source_max - source_min),
    "floorOffset_m": floor_offset,
}
Path(MANIFEST).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("PERSONAL_TWIN_STANDING=" + json.dumps(payload, separators=(",", ":")))
