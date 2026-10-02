#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.sse import sse_client

ACTION = sys.argv[1] if len(sys.argv) > 1 else "measure"
if ACTION not in {"measure", "fit", "validate"}:
    raise SystemExit(f"unsupported action: {ACTION}")

PROFILE_PATH = Path("/data/canonical/body/profile.json")
if not PROFILE_PATH.exists():
    raise SystemExit(f"canonical body profile missing: {PROFILE_PATH}")

profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
measurements = profile.get("measurements", {})


def mm(name: str) -> float | None:
    item = measurements.get(name)
    if not isinstance(item, dict):
        return None
    value = item.get("value")
    return float(value) if value is not None else None


def foot_mm() -> float | None:
    foot = measurements.get("foot")
    if not isinstance(foot, dict):
        return None
    values: list[float] = []
    for side in ("left", "right"):
        length = (foot.get(side) or {}).get("length") or {}
        if length.get("value") is not None:
            values.append(float(length["value"]))
    return sum(values) / len(values) if values else None


canonical = {
    "height_mm": mm("height"),
    "shoulderBreadth_mm": mm("shoulderBreadth"),
    "chestCircumference_mm": mm("chestCircumference"),
    "waistCircumference_mm": mm("waistCircumference"),
    "hipCircumference_mm": mm("hipCircumference"),
    "armLength_mm": mm("armLength"),
    "inseam_mm": mm("inseam"),
    "sittingHeight_mm": mm("sittingHeight"),
    "footLength_mm": foot_mm(),
}

prefix = (
    "ACTION = " + repr(ACTION) + "\n"
    "PROFILE_ID = " + repr(profile.get("profileId", "me")) + "\n"
    "CANONICAL = " + repr(canonical) + "\n"
)

BLENDER_CODE = r'''
import bpy
import json
import math
from collections import defaultdict
from mathutils import Vector
from bl_ext.user_default.mpfb.services.targetservice import TargetService

OBJECT_NAME = "PersonalTwinAvatar"
BODY_REPORT = "/data/body/body-measurements.json"
LANDMARK_REPORT = "/data/body/landmarks.json"
FIT_REPORT = "/data/body/avatar-fit.json"
AVATAR_PATH = "/data/body/avatar.blend"

# MPFB hm08 fixed-topology landmarks.
CROTCH_VERTEX_IDS = [4425, 11043, 6395, 12992]
SEAT_VERTEX_IDS = [4455, 11073]
CROWN_VERTEX_IDS = [881]

TOLERANCES_MM = {
    "height_mm": 5.0,
    "chestCircumference_mm": 5.0,
    "inseam_mm": 10.0,
}

obj = bpy.data.objects.get(OBJECT_NAME)
if obj is None or obj.type != "MESH":
    raise RuntimeError(f"{OBJECT_NAME} mesh is not loaded")


def _group_ids(name):
    group = obj.vertex_groups.get(name)
    if group is None:
        return []
    result = []
    for vertex in obj.data.vertices:
        for membership in vertex.groups:
            if membership.group == group.index and membership.weight > 0:
                result.append(vertex.index)
                break
    return result


BODY_IDS = set(_group_ids("body"))
if not BODY_IDS:
    raise RuntimeError("MPFB body vertex group is missing or empty")


def _final_coords():
    keys = obj.data.shape_keys.key_blocks if obj.data.shape_keys else None
    if not keys:
        return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    basis = keys[0]
    coords = [Vector(basis.data[index].co) for index in range(len(basis.data))]
    for key in keys[1:]:
        value = float(key.value)
        if abs(value) < 1e-12:
            continue
        for index in range(len(coords)):
            coords[index] += (key.data[index].co - basis.data[index].co) * value
    return [obj.matrix_world @ point for point in coords]


def _average_point(coords, indices):
    if not indices:
        raise RuntimeError("landmark has no vertices")
    if max(indices) >= len(coords):
        raise RuntimeError("landmark topology is incompatible with this mesh")
    return sum((coords[index] for index in indices), Vector()) / len(indices)


def _group_centroid(coords, name):
    indices = _group_ids(name)
    if not indices:
        raise RuntimeError(f"required MPFB vertex group is missing: {name}")
    return _average_point(coords, indices)


def _verify_topology(coords):
    landmark_ids = CROTCH_VERTEX_IDS + SEAT_VERTEX_IDS + CROWN_VERTEX_IDS
    if len(coords) <= max(landmark_ids):
        raise RuntimeError("MPFB hm08 topology has fewer vertices than the landmark contract expects")

    crotch = [coords[index] for index in CROTCH_VERTEX_IDS]
    seat = [coords[index] for index in SEAT_VERTEX_IDS]
    crown = _average_point(coords, CROWN_VERTEX_IDS)

    if abs(crotch[0].x + crotch[1].x) > 0.006 or abs(crotch[2].x + crotch[3].x) > 0.006:
        raise RuntimeError("crotch landmark symmetry check failed")
    if abs(seat[0].x + seat[1].x) > 0.006:
        raise RuntimeError("seat landmark symmetry check failed")

    body_top = max(coords[index].z for index in BODY_IDS)
    if abs(crown.z - body_top) > 0.025:
        raise RuntimeError("crown landmark is no longer near the top of the body mesh")


def _section_loops(coords, z, epsilon=2e-5):
    """Intersect the body triangle mesh with z=constant and return closed XY loops."""
    obj.data.calc_loop_triangles()
    segments = []

    for triangle in obj.data.loop_triangles:
        ids = list(triangle.vertices)
        if not all(index in BODY_IDS for index in ids):
            continue

        intersections = []
        for a, b in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            p, q = coords[a], coords[b]
            da, db = p.z - z, q.z - z
            if abs(da) < 1e-10 and abs(db) < 1e-10:
                continue
            if da * db > 0 or abs(q.z - p.z) < 1e-12:
                continue
            t = (z - p.z) / (q.z - p.z)
            if -1e-8 <= t <= 1 + 1e-8:
                point = p + (q - p) * t
                intersections.append(Vector((point.x, point.y, 0.0)))

        unique = []
        for point in intersections:
            if not any((point - other).length < epsilon for other in unique):
                unique.append(point)
        if len(unique) == 2 and (unique[0] - unique[1]).length > epsilon:
            segments.append((unique[0], unique[1]))

    def key(point):
        return (round(point.x / epsilon), round(point.y / epsilon))

    raw_points = defaultdict(list)
    adjacency = defaultdict(list)
    for a, b in segments:
        ka, kb = key(a), key(b)
        raw_points[ka].append(a)
        raw_points[kb].append(b)
        if kb not in adjacency[ka]:
            adjacency[ka].append(kb)
        if ka not in adjacency[kb]:
            adjacency[kb].append(ka)

    positions = {node: sum(points, Vector()) / len(points) for node, points in raw_points.items()}
    seen_edges = set()
    loops = []

    for start in list(adjacency):
        for first_next in adjacency[start]:
            if frozenset((start, first_next)) in seen_edges:
                continue

            path = [start]
            previous = None
            current = start
            next_node = first_next

            for _ in range(len(adjacency) + 5):
                seen_edges.add(frozenset((current, next_node)))
                previous, current = current, next_node
                path.append(current)
                if current == start:
                    break

                choices = [candidate for candidate in adjacency[current] if candidate != previous]
                if not choices:
                    break
                next_node = choices[0]

            if len(path) < 4 or path[-1] != start:
                continue

            points = [positions[node] for node in path[:-1]]
            perimeter = sum(
                (points[index] - points[(index + 1) % len(points)]).length
                for index in range(len(points))
            )
            centroid_x = sum(point.x for point in points) / len(points)
            centroid_y = sum(point.y for point in points) / len(points)
            area = abs(
                sum(
                    points[index].x * points[(index + 1) % len(points)].y
                    - points[(index + 1) % len(points)].x * points[index].y
                    for index in range(len(points))
                )
                / 2
            )
            loops.append(
                {
                    "pointCount": len(points),
                    "perimeter_m": perimeter,
                    "centroid": [centroid_x, centroid_y],
                    "area_m2": area,
                }
            )

    loops.sort(key=lambda loop: loop["area_m2"], reverse=True)
    return loops


def _chest_measurement(coords):
    nipple_group = "nippleTip" if _group_ids("nippleTip") else "nipple"
    chest_plane = _group_centroid(coords, nipple_group)
    loops = _section_loops(coords, chest_plane.z)
    central = [loop for loop in loops if abs(loop["centroid"][0]) < 0.08]
    if not central:
        raise RuntimeError("no central torso loop found at the chest plane")
    torso = max(central, key=lambda loop: loop["area_m2"])
    other_loops = [loop for loop in loops if loop is not torso]
    return {
        "circumference_mm": torso["perimeter_m"] * 1000,
        "planeZ_mm": chest_plane.z * 1000,
        "torsoLoop": torso,
        "otherLoops": other_loops,
        "planeLandmarkGroup": nipple_group,
    }


def _visible_body_height(coords):
    points = [coords[index] for index in BODY_IDS]
    return (max(point.z for point in points) - min(point.z for point in points)) * 1000


def _foot_length(coords, side):
    points = [
        coords[index]
        for index in BODY_IDS
        if coords[index].z < 0.205
        and (coords[index].x > 0 if side == "left" else coords[index].x < 0)
    ]
    if not points:
        raise RuntimeError(f"no {side} foot points found")
    return (max(point.y for point in points) - min(point.y for point in points)) * 1000


def _measure():
    coords = _final_coords()
    _verify_topology(coords)

    ground = _group_centroid(coords, "joint-ground")
    crotch = _average_point(coords, CROTCH_VERTEX_IDS)
    seat = _average_point(coords, SEAT_VERTEX_IDS)
    crown = _average_point(coords, CROWN_VERTEX_IDS)
    chest = _chest_measurement(coords)

    left_shoulder = _group_centroid(coords, "joint-l-shoulder")
    right_shoulder = _group_centroid(coords, "joint-r-shoulder")
    left_elbow = _group_centroid(coords, "joint-l-elbow")
    left_hand = _group_centroid(coords, "joint-l-hand")

    height = _visible_body_height(coords)
    shoulder = (left_shoulder - right_shoulder).length * 1000
    arm = ((left_shoulder - left_elbow).length + (left_elbow - left_hand).length) * 1000

    return {
        "schemaVersion": 1,
        "profileId": PROFILE_ID,
        "measurements": {
            "height_mm": height,
            "shoulderBreadthProxy_mm": shoulder,
            "armChainProxy_mm": arm,
            "leftFootLengthProxy_mm": _foot_length(coords, "left"),
            "rightFootLengthProxy_mm": _foot_length(coords, "right"),
            "chestCircumference_mm": chest["circumference_mm"],
            "inseam_mm": (crotch.z - ground.z) * 1000,
            "sittingHeight_mm": (crown.z - seat.z) * 1000,
        },
        "chest": chest,
        "landmarks": {
            "ground": {
                "kind": "vertexGroupCentroid",
                "group": "joint-ground",
                "xyz_mm": [ground.x * 1000, ground.y * 1000, ground.z * 1000],
            },
            "crotch": {
                "kind": "vertexAverage",
                "vertexIds": CROTCH_VERTEX_IDS,
                "xyz_mm": [crotch.x * 1000, crotch.y * 1000, crotch.z * 1000],
            },
            "seatPlane": {
                "kind": "bilateralVertexAverage",
                "vertexIds": SEAT_VERTEX_IDS,
                "xyz_mm": [seat.x * 1000, seat.y * 1000, seat.z * 1000],
            },
            "crown": {
                "kind": "vertexAverage",
                "vertexIds": CROWN_VERTEX_IDS,
                "xyz_mm": [crown.x * 1000, crown.y * 1000, crown.z * 1000],
            },
        },
    }


def _remove_target(name):
    if not obj.data.shape_keys:
        return
    key = obj.data.shape_keys.key_blocks.get(name)
    if key is not None:
        obj.shape_key_remove(key)


def _fit_height(target_mm):
    baseline = _visible_body_height(_final_coords())
    if baseline <= 0:
        raise RuntimeError("visible body height is invalid")

    factor = target_mm / baseline
    obj.scale.z *= factor
    bpy.context.view_layer.update()

    fitted = _visible_body_height(_final_coords())
    return {
        "axis": "z",
        "factor": factor,
        "baseline_mm": baseline,
        "fitted_mm": fitted,
        "objectScaleZ": float(obj.scale.z),
    }


def _fit_chest(target_mm):
    for name in ("measure-bust-circ-decr", "measure-bust-circ-incr"):
        _remove_target(name)

    baseline = _chest_measurement(_final_coords())["circumference_mm"]
    if abs(target_mm - baseline) <= 0.25:
        return {"target": None, "weight": 0.0, "baseline_mm": baseline, "fitted_mm": baseline}

    target_name = "measure-bust-circ-decr" if target_mm < baseline else "measure-bust-circ-incr"
    path = TargetService.target_full_path(target_name)
    if not path:
        raise RuntimeError(f"MPFB target not found: {target_name}")

    key = TargetService.load_target(obj, path, weight=0.0, name=target_name)
    key.value = 1.0
    endpoint = _chest_measurement(_final_coords())["circumference_mm"]

    reachable_low, reachable_high = sorted((baseline, endpoint))
    if not reachable_low <= target_mm <= reachable_high:
        obj.shape_key_remove(key)
        raise RuntimeError(
            f"chest target {target_mm:.2f} mm is outside MPFB target range "
            f"{reachable_low:.2f}..{reachable_high:.2f} mm"
        )

    low, high = 0.0, 1.0
    increasing = endpoint > baseline
    for _ in range(12):
        mid = (low + high) / 2
        key.value = mid
        measured = _chest_measurement(_final_coords())["circumference_mm"]
        if (measured < target_mm) == increasing:
            low = mid
        else:
            high = mid

    key.value = (low + high) / 2
    fitted = _chest_measurement(_final_coords())["circumference_mm"]
    return {
        "target": target_name,
        "weight": float(key.value),
        "baseline_mm": baseline,
        "endpoint_mm": endpoint,
        "fitted_mm": fitted,
    }


def _validation(report):
    measured = report["measurements"]
    mapping = {
        "height_mm": "height_mm",
        "chestCircumference_mm": "chestCircumference_mm",
        "inseam_mm": "inseam_mm",
    }

    checks = {}
    all_ok = True
    for canonical_name, measured_name in mapping.items():
        target = CANONICAL.get(canonical_name)
        value = measured.get(measured_name)
        if target is None:
            checks[canonical_name] = {"status": "missing-canonical"}
            continue

        tolerance = TOLERANCES_MM[canonical_name]
        error = value - target
        ok = abs(error) <= tolerance
        all_ok = all_ok and ok
        checks[canonical_name] = {
            "status": "ok" if ok else "out-of-tolerance",
            "target_mm": target,
            "measured_mm": value,
            "error_mm": error,
            "tolerance_mm": tolerance,
        }

    return {"ok": all_ok, "checks": checks}


fit_result = None
if ACTION == "fit":
    height_target = CANONICAL.get("height_mm")
    chest_target = CANONICAL.get("chestCircumference_mm")
    if height_target is None:
        raise RuntimeError("canonical height is required for fit")
    if chest_target is None:
        raise RuntimeError("canonical chestCircumference is required for fit")

    fit_result = {
        "height": _fit_height(float(height_target)),
        "chest": _fit_chest(float(chest_target)),
    }

report = _measure()
validation = _validation(report)
report["validation"] = validation
if fit_result is not None:
    report["fit"] = fit_result

landmark_report = {
    "schemaVersion": 1,
    "topology": "MPFB hm08",
    "profileId": PROFILE_ID,
    "landmarks": report["landmarks"],
    "measurementDefinitions": {
        "chestCircumference": "Closed main torso mesh intersection loop at nippleTip/nipple centroid Z; arm loops are excluded.",
        "inseam": "Vertical distance from joint-ground centroid to the fixed crotch topology landmark.",
        "sittingHeight": "Neutral-pose structural proxy from the bilateral seat-support topology landmark to the crown. Canonical sitting height is enforced by the seated ergonomics pose, not by neutral-body validation.",
    },
}

with open(BODY_REPORT, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
    handle.write("\n")
with open(LANDMARK_REPORT, "w", encoding="utf-8") as handle:
    json.dump(landmark_report, handle, ensure_ascii=False, indent=2)
    handle.write("\n")

if ACTION == "fit":
    existing = {}
    try:
        with open(FIT_REPORT, "r", encoding="utf-8") as handle:
            existing = json.load(handle)
    except FileNotFoundError:
        pass

    existing["measurementInfrastructureVersion"] = "body-visible-height-v2"
    existing["measurementValidation"] = validation
    existing.setdefault("directlyFitted", [])
    if "chestCircumference" not in existing["directlyFitted"]:
        existing["directlyFitted"].append("chestCircumference")
    if "constraintOnly" in existing:
        existing["constraintOnly"] = [
            name for name in existing["constraintOnly"] if name != "chestCircumference"
        ]
    existing["validatedConstraints"] = ["inseam"]
    existing["heightFit"] = fit_result["height"]
    existing["chestFit"] = fit_result["chest"]
    existing.setdefault("measuredAfterFit", {})
    existing["measuredAfterFit"]["height_mm"] = report["measurements"]["height_mm"]
    existing["measuredAfterFit"]["chestCircumference_mm"] = report["measurements"]["chestCircumference_mm"]
    existing["measuredAfterFit"]["inseam_mm"] = report["measurements"]["inseam_mm"]
    existing["measuredAfterFit"]["sittingHeight_mm"] = report["measurements"]["sittingHeight_mm"]
    existing["landmarkReports"] = {
        "measurements": BODY_REPORT,
        "landmarks": LANDMARK_REPORT,
    }
    with open(FIT_REPORT, "w", encoding="utf-8") as handle:
        json.dump(existing, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    bpy.ops.wm.save_as_mainfile(filepath=AVATAR_PATH)

result = report
'''

async def main() -> int:
    code = prefix + BLENDER_CODE
    async with sse_client("http://127.0.0.1:9878/sse") as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool("execute_blender_code", {"code": code})
            if response.isError:
                raise RuntimeError(response.content)
            payload = response.structuredContent or {}
            result = payload.get("result", payload)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if ACTION == "validate" and not result.get("validation", {}).get("ok", False):
                return 1
            return 0


raise SystemExit(asyncio.run(main()))
