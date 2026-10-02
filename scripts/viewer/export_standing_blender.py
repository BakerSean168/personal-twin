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


def body_vertex_ids(obj):
    group = obj.vertex_groups.get("body")
    if group is None:
        return list(range(len(obj.data.vertices)))
    ids = []
    for vertex in obj.data.vertices:
        for membership in vertex.groups:
            if membership.group == group.index and membership.weight > 0:
                ids.append(vertex.index)
                break
    return ids


BODY_IDS = body_vertex_ids(body)


def final_shape_bounds(obj):
    keys = obj.data.shape_keys.key_blocks if obj.data.shape_keys else None
    if not keys:
        coords = [Vector(vertex.co) for vertex in obj.data.vertices]
    else:
        basis = keys[0]
        coords = [Vector(basis.data[index].co) for index in range(len(basis.data))]
        for key in keys[1:]:
            value = float(key.value)
            if abs(value) < 1e-12:
                continue
            for index in range(len(coords)):
                coords[index] += (key.data[index].co - basis.data[index].co) * value

    minimum = Vector((1e18, 1e18, 1e18))
    maximum = Vector((-1e18, -1e18, -1e18))
    for index in BODY_IDS:
        point = obj.matrix_world @ coords[index]
        for axis in range(3):
            minimum[axis] = min(minimum[axis], point[axis])
            maximum[axis] = max(maximum[axis], point[axis])
    return minimum, maximum


# Export the fitted neutral avatar exactly as derived from canonical body facts.
# The Web view gets a presentation-only floor normalization; the neutral blend
# file itself is never saved or mutated on disk.
source_min, source_max = final_shape_bounds(body)
floor_offset = -source_min.z
body.location.z += floor_offset
bpy.context.view_layer.update()

for obj in bpy.context.scene.objects:
    obj.select_set(False)
body.select_set(True)
bpy.context.view_layer.objects.active = body

bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format="GLB",
    use_selection=True,
    export_apply=False,
    export_all_influences=True,
)

normalized_min, normalized_max = final_shape_bounds(body)
payload = {
    "schemaVersion": 1,
    "kind": "standing-avatar",
    "source": "/data/body/avatar.blend",
    "object": body.name,
    "sourceBounds_m": {"min": list(source_min), "max": list(source_max)},
    "normalizedBounds_m": {"min": list(normalized_min), "max": list(normalized_max)},
    "dimensions_m": list(source_max - source_min),
    "floorOffset_m": floor_offset,
}
Path(MANIFEST).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("PERSONAL_TWIN_STANDING=" + json.dumps(payload, separators=(",", ":")))
