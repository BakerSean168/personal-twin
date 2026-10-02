#!/usr/bin/env python3
from __future__ import annotations

import bpy
import bmesh
import json
from pathlib import Path

ASSETS = Path("/data/viewer/assets")
OUTPUTS = [
    ("room.glb", "room-cutaway.glb"),
    ("scene-combined.glb", "scene-combined-cutaway.glb"),
]
META = ASSETS / "cutaway.json"

# Presentation-only margins relative to the current room mesh bounds.
# They are generic viewer constants, not measurements from a specific home.
CEILING_BAND_M = 0.25
FRONT_BAND_M = 0.35
FLOOR_GUARD_M = 0.05
TOP_NORMAL_Z_MIN = 0.80


def cut_room_shell(obj: bpy.types.Object) -> dict:
    if obj.type != "MESH":
        raise RuntimeError(f"{obj.name} is not a mesh")

    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    world_vertices = [obj.matrix_world @ vertex.co for vertex in bm.verts]
    if not world_vertices:
        bm.free()
        raise RuntimeError("room mesh has no vertices")

    max_y = max(point.y for point in world_vertices)
    min_z = min(point.z for point in world_vertices)
    max_z = max(point.z for point in world_vertices)

    front_threshold = max_y - FRONT_BAND_M
    floor_threshold = min_z + FLOOR_GUARD_M
    ceiling_threshold = max_z - CEILING_BAND_M

    delete_faces = []
    top_count = 0
    front_count = 0

    for face in bm.faces:
        center = obj.matrix_world @ face.calc_center_median()
        normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()

        is_top = (
            center.z > ceiling_threshold
            and abs(normal.z) > TOP_NORMAL_Z_MIN
        )
        # Presentation cut: remove the complete observation-side shell,
        # including window/frame/glass and wall-mounted details. Preserve the
        # floor with a small bounds-relative guard band.
        is_front = (
            center.y > front_threshold
            and center.z > floor_threshold
        )

        if is_top or is_front:
            delete_faces.append(face)
            top_count += int(is_top)
            front_count += int(is_front)

    if not delete_faces:
        bm.free()
        raise RuntimeError("cutaway rule matched no room faces")

    unique_faces = list({face.index: face for face in delete_faces}.values())
    bmesh.ops.delete(bm, geom=unique_faces, context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    return {
        "deletedFaces": len(unique_faces),
        "topFaces": top_count,
        "frontWallFaces": front_count,
        "frontAxis": "+Y",
        "thresholds_m": {
            "frontY": front_threshold,
            "floorZ": floor_threshold,
            "ceilingZ": ceiling_threshold,
        },
    }


results = {}
for source_name, output_name in OUTPUTS:
    source = ASSETS / source_name
    if not source.is_file():
        continue

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(source))

    room = bpy.data.objects.get("export")
    if room is None:
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        if source_name == "room.glb" and len(meshes) == 1:
            room = meshes[0]
        else:
            raise RuntimeError(f"could not identify room mesh in {source_name}")

    result = cut_room_shell(room)
    output = ASSETS / output_name

    bpy.ops.export_scene.gltf(
        filepath=str(output),
        export_format="GLB",
        use_selection=False,
        export_apply=True,
    )

    results[output_name] = {
        "source": source_name,
        **result,
    }

payload = {
    "schemaVersion": 2,
    "kind": "viewer-cutaway",
    "presentationOnly": True,
    "rule": {
        "ceilingBand_m": CEILING_BAND_M,
        "frontBand_m": FRONT_BAND_M,
        "floorGuard_m": FLOOR_GUARD_M,
        "topNormalZMin": TOP_NORMAL_Z_MIN,
        "description": (
            "remove near-ceiling horizontal faces and all room-mesh geometry "
            "within the observation-side +Y boundary band"
        ),
    },
    "outputs": results,
}
META.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
print("PERSONAL_TWIN_CUTAWAY=" + json.dumps(payload, separators=(",", ":")))
