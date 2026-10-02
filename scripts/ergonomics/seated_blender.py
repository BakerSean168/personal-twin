#!/usr/bin/env python3
import sys

ACTION = "build"
if "--" in sys.argv:
    args = sys.argv[sys.argv.index("--") + 1:]
    if len(args) >= 2 and args[0] == "--action":
        ACTION = args[1]
if ACTION not in {"build", "validate"}:
    raise RuntimeError("unsupported action: " + ACTION)


import bpy
import json
import math
import os
from mathutils import Vector
from bl_ext.user_default.mpfb.services.humanservice import HumanService

NEUTRAL_PATH = "/data/body/avatar.blend"
SEATED_PATH = "/data/ergonomics/avatar-seated.blend"
GLB_PATH = "/data/ergonomics/avatar-seated.glb"
REPORT_PATH = "/data/ergonomics/seated-v1-report.json"
PROFILE_PATH = "/data/canonical/body/profile.json"
SETUP_PATH = "/data/canonical/ergonomics/desk-setup.json"

POSE_VERSION = "seated-v1"
HIP_DEG = -67.0
KNEE_DEG = 67.0
FOOT_FLOOR_TOL_MM = 10.0
CROWN_TOL_MM = 5.0
WRIST_TOL_MM = 5.0
SYMMETRY_TOL_MM = 2.0

with open(PROFILE_PATH, "r", encoding="utf-8") as handle:
    profile = json.load(handle)
with open(SETUP_PATH, "r", encoding="utf-8") as handle:
    setup = json.load(handle)


def _mm_measurement(name):
    item = profile.get("measurements", {}).get(name)
    if not isinstance(item, dict) or item.get("value") is None:
        raise RuntimeError(f"canonical body measurement is missing: {name}")
    if item.get("unit") != "mm":
        raise RuntimeError(f"{name} must be stored in mm")
    return float(item["value"])


def _m(value_mm):
    return float(value_mm) / 1000.0


def _object_spec(name):
    item = setup.get("objects", {}).get(name)
    if not isinstance(item, dict):
        raise RuntimeError(f"ergonomic setup object is missing: {name}")
    return item


def _dims_m(item):
    return _m(item["width"]), _m(item["depth"]), _m(item["height"])


def _center_xy_m(item):
    return _m(item["center"]["x"]), _m(item["center"]["y"])


def _box(name, size, location, collection):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for previous in list(obj.users_collection):
        previous.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def _empty(name, location, collection):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "SPHERE"
    obj.empty_display_size = 0.025
    obj.location = location
    collection.objects.link(obj)
    return obj


def _body_group_ids(mesh, name):
    group = mesh.vertex_groups.get(name)
    if group is None:
        return []
    ids = []
    for vertex in mesh.data.vertices:
        for membership in vertex.groups:
            if membership.group == group.index and membership.weight > 0:
                ids.append(vertex.index)
                break
    return ids


def _evaluated_coords(mesh):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(depsgraph)
    evaluated_mesh = evaluated.to_mesh()
    if len(evaluated_mesh.vertices) != len(mesh.data.vertices):
        evaluated.to_mesh_clear()
        raise RuntimeError(
            f"evaluated topology mismatch: {len(evaluated_mesh.vertices)} != {len(mesh.data.vertices)}"
        )
    coords = [evaluated.matrix_world @ vertex.co for vertex in evaluated_mesh.vertices]
    evaluated.to_mesh_clear()
    return coords


def _centroid(coords, ids):
    if not ids:
        raise RuntimeError("cannot calculate centroid of an empty landmark")
    return sum((coords[index] for index in ids), Vector()) / len(ids)


def _pose_bone_world_point(rig, bone_name, which="head"):
    bone = rig.pose.bones[bone_name]
    point = bone.head if which == "head" else bone.tail
    return rig.matrix_world @ point


def _environment(collection):
    stool = _object_spec("stool")
    desk = _object_spec("desk")
    monitor = _object_spec("monitor")
    keyboard = _object_spec("keyboard")
    mouse = _object_spec("mouse")
    laptop = _object_spec("laptop")

    # Floor reference.
    _box("Ergo_Floor", (2.6, 2.4, 0.01), (0.0, -0.45, -0.005), collection)

    # Stool: thin seat slab plus four simple legs, preserving the measured top height.
    sw, sd, sh = _dims_m(stool)
    sx, sy = _center_xy_m(stool)
    seat_thickness = 0.04
    _box("Ergo_Stool_Seat", (sw, sd, seat_thickness), (sx, sy, sh - seat_thickness / 2), collection)
    leg_size = 0.025
    leg_z = (sh - seat_thickness) / 2
    for ix, dx in enumerate((-sw / 2 + 0.04, sw / 2 - 0.04)):
        for iy, dy in enumerate((-sd / 2 + 0.04, sd / 2 - 0.04)):
            _box(
                f"Ergo_Stool_Leg_{ix}_{iy}",
                (leg_size, leg_size, sh - seat_thickness),
                (sx + dx, sy + dy, leg_z),
                collection,
            )

    # Desk: top slab plus legs. The canonical height is the top surface.
    dw, dd, dh = _dims_m(desk)
    dx, dy = _center_xy_m(desk)
    desk_thickness = 0.04
    _box("Ergo_Desk_Top", (dw, dd, desk_thickness), (dx, dy, dh - desk_thickness / 2), collection)
    desk_leg = 0.045
    desk_leg_h = dh - desk_thickness
    for ix, ox in enumerate((-dw / 2 + 0.06, dw / 2 - 0.06)):
        for iy, oy in enumerate((-dd / 2 + 0.06, dd / 2 - 0.06)):
            _box(
                f"Ergo_Desk_Leg_{ix}_{iy}",
                (desk_leg, desk_leg, desk_leg_h),
                (dx + ox, dy + oy, desk_leg_h / 2),
                collection,
            )

    def place_measured_box(key, object_name):
        item = _object_spec(key)
        width, depth, height = _dims_m(item)
        x, y = _center_xy_m(item)
        bottom = _m(item.get("bottomZ", 0))
        return _box(object_name, (width, depth, height), (x, y, bottom + height / 2), collection)

    place_measured_box("monitor", "Ergo_Monitor")
    place_measured_box("keyboard", "Ergo_Keyboard")
    place_measured_box("mouse", "Ergo_Mouse")
    place_measured_box("laptop", "Ergo_Laptop")


def _create_pose():
    body = bpy.data.objects.get("PersonalTwinAvatar")
    if body is None:
        raise RuntimeError("neutral PersonalTwinAvatar is missing")

    rig = HumanService.add_builtin_rig(body, "default", import_weights=True)
    rig.name = "PersonalTwinAvatar.SeatedRig"

    # Keep original topology available for measurement while posing.
    masks = [modifier for modifier in body.modifiers if modifier.type == "MASK"]
    for modifier in masks:
        modifier.show_viewport = False

    # Symmetric sagittal-plane lower-body pose. With the fitted 172 cm avatar,
    # -67/+67 locks the measured sitting height while placing the feet on the floor.
    for side in ("L", "R"):
        hip = rig.pose.bones[f"upperleg01.{side}"]
        knee = rig.pose.bones[f"lowerleg01.{side}"]
        hip.rotation_mode = "XYZ"
        knee.rotation_mode = "XYZ"
        hip.rotation_euler = (math.radians(HIP_DEG), 0.0, 0.0)
        knee.rotation_euler = (math.radians(KNEE_DEG), 0.0, 0.0)

    bpy.context.view_layer.update()

    body_ids = _body_group_ids(body, "body")
    coords = _evaluated_coords(body)
    crown_z = max(coords[index].z for index in body_ids)

    seat_height = _m(_object_spec("stool")["height"])
    sitting_height = _m(_mm_measurement("sittingHeight"))
    target_crown_z = seat_height + sitting_height
    rig.location.z += target_crown_z - crown_z

    bpy.context.view_layer.update()

    keyboard = _object_spec("keyboard")
    keyboard_x, keyboard_y = _center_xy_m(keyboard)
    keyboard_width, keyboard_depth, keyboard_height = _dims_m(keyboard)
    keyboard_top = _m(keyboard["bottomZ"]) + keyboard_height
    keyboard_near_y = keyboard_y + keyboard_depth / 2

    targets = bpy.data.collections.new("Ergo_PoseTargets")
    bpy.context.scene.collection.children.link(targets)

    wrist_target_y = keyboard_near_y - 0.0125
    wrist_target_z = keyboard_top - 0.004
    wrist_target_x = min(keyboard_width / 2, 0.18)

    # Arm IK without pole targets preserves exact bilateral mirror symmetry.
    for side, sign in (("L", 1.0), ("R", -1.0)):
        target = _empty(
            f"Ergo_WristTarget.{side}",
            (keyboard_x + sign * wrist_target_x, wrist_target_y, wrist_target_z),
            targets,
        )
        forearm = rig.pose.bones[f"lowerarm02.{side}"]
        constraint = forearm.constraints.new("IK")
        constraint.name = "PersonalTwin keyboard IK"
        constraint.target = target
        constraint.chain_count = 4

    environment = bpy.data.collections.new("Ergo_Environment")
    bpy.context.scene.collection.children.link(environment)
    _environment(environment)

    bpy.context.view_layer.update()

    body["personal_twin_pose_version"] = POSE_VERSION
    body["personal_twin_pose_source"] = "canonical body + ergonomic desk setup"
    rig["personal_twin_pose_version"] = POSE_VERSION
    bpy.context.scene["personal_twin_pose_version"] = POSE_VERSION

    for modifier in masks:
        modifier.show_viewport = True

    return body, rig, {
        "targetCrownZ_m": target_crown_z,
        "wristTarget": {
            "x_m": wrist_target_x,
            "y_m": wrist_target_y,
            "z_m": wrist_target_z,
        },
    }


def _report(body, rig, pose_targets):
    masks = [modifier for modifier in body.modifiers if modifier.type == "MASK"]
    for modifier in masks:
        modifier.show_viewport = False
    bpy.context.view_layer.update()

    coords = _evaluated_coords(body)
    body_ids = _body_group_ids(body, "body")
    body_points = [coords[index] for index in body_ids]

    stool = _object_spec("stool")
    desk = _object_spec("desk")
    monitor = _object_spec("monitor")
    keyboard = _object_spec("keyboard")

    seat_w, seat_d, seat_h = _dims_m(stool)
    seat_x, seat_y = _center_xy_m(stool)
    desk_w, desk_d, desk_h = _dims_m(desk)
    keyboard_w, keyboard_d, keyboard_h = _dims_m(keyboard)
    keyboard_x, keyboard_y = _center_xy_m(keyboard)
    keyboard_top = _m(keyboard["bottomZ"]) + keyboard_h

    crown = max(point.z for point in body_points)
    floor_gap = min(point.z for point in body_points)

    seat_candidates = [
        point.z
        for point in body_points
        if seat_x - seat_w / 2 <= point.x <= seat_x + seat_w / 2
        and seat_y - seat_d / 2 <= point.y <= seat_y + seat_d / 2
        and seat_h - 0.10 <= point.z <= seat_h + 0.20
    ]
    seat_surface_low = min(seat_candidates) if seat_candidates else None
    seat_gap = None if seat_surface_low is None else seat_surface_low - seat_h

    eye_ids = _body_group_ids(body, "joint-l-eye") + _body_group_ids(body, "joint-r-eye")
    eye = _centroid(coords, eye_ids)

    monitor_x, monitor_y = _center_xy_m(monitor)
    monitor_w, monitor_d, monitor_h = _dims_m(monitor)
    monitor_bottom = _m(monitor["bottomZ"])
    monitor_center_z = monitor_bottom + monitor_h / 2
    monitor_top = monitor_bottom + monitor_h
    view_distance = abs(eye.y - monitor_y)

    wrist_l = _pose_bone_world_point(rig, "wrist.L", "head")
    wrist_r = _pose_bone_world_point(rig, "wrist.R", "head")
    knee_l = _pose_bone_world_point(rig, "lowerleg01.L", "head")
    knee_r = _pose_bone_world_point(rig, "lowerleg01.R", "head")

    wrist_target_z = pose_targets["wristTarget"]["z_m"]
    symmetry = {
        "wrist_x_sum_mm": (wrist_l.x + wrist_r.x) * 1000,
        "wrist_y_diff_mm": (wrist_l.y - wrist_r.y) * 1000,
        "wrist_z_diff_mm": (wrist_l.z - wrist_r.z) * 1000,
        "knee_x_sum_mm": (knee_l.x + knee_r.x) * 1000,
        "knee_y_diff_mm": (knee_l.y - knee_r.y) * 1000,
        "knee_z_diff_mm": (knee_l.z - knee_r.z) * 1000,
    }

    target_crown = pose_targets["targetCrownZ_m"]
    checks = {
        "crown": {
            "target_mm": target_crown * 1000,
            "measured_mm": crown * 1000,
            "error_mm": (crown - target_crown) * 1000,
            "tolerance_mm": CROWN_TOL_MM,
        },
        "feet": {
            "target_mm": 0.0,
            "measured_mm": floor_gap * 1000,
            "error_mm": floor_gap * 1000,
            "tolerance_mm": FOOT_FLOOR_TOL_MM,
        },
        "leftWristHeight": {
            "target_mm": wrist_target_z * 1000,
            "measured_mm": wrist_l.z * 1000,
            "error_mm": (wrist_l.z - wrist_target_z) * 1000,
            "tolerance_mm": WRIST_TOL_MM,
        },
        "rightWristHeight": {
            "target_mm": wrist_target_z * 1000,
            "measured_mm": wrist_r.z * 1000,
            "error_mm": (wrist_r.z - wrist_target_z) * 1000,
            "tolerance_mm": WRIST_TOL_MM,
        },
    }
    for check in checks.values():
        check["status"] = "ok" if abs(check["error_mm"]) <= check["tolerance_mm"] else "out-of-tolerance"

    symmetry_error = max(abs(value) for value in symmetry.values())
    checks["bilateralSymmetry"] = {
        "target_mm": 0.0,
        "measured_mm": symmetry_error,
        "error_mm": symmetry_error,
        "tolerance_mm": SYMMETRY_TOL_MM,
        "status": "ok" if symmetry_error <= SYMMETRY_TOL_MM else "out-of-tolerance",
    }

    validation_ok = all(check["status"] == "ok" for check in checks.values())

    report = {
        "schemaVersion": 1,
        "poseVersion": POSE_VERSION,
        "profileId": profile.get("profileId", "me"),
        "setupId": setup.get("setupId"),
        "pose": {
            "hipFlexionPreset_deg": abs(HIP_DEG),
            "kneeCounterRotationPreset_deg": KNEE_DEG,
            "torso": "upright-neutral",
            "handTarget": "keyboard",
        },
        "geometry": {
            "seatTop_mm": seat_h * 1000,
            "deskTop_mm": desk_h * 1000,
            "seatToDeskTop_mm": (desk_h - seat_h) * 1000,
            "crownHeight_mm": crown * 1000,
            "footFloorGap_mm": floor_gap * 1000,
            "seatSurfaceGapProxy_mm": None if seat_gap is None else seat_gap * 1000,
            "leftWrist_mm": [wrist_l.x * 1000, wrist_l.y * 1000, wrist_l.z * 1000],
            "rightWrist_mm": [wrist_r.x * 1000, wrist_r.y * 1000, wrist_r.z * 1000],
            "leftKnee_mm": [knee_l.x * 1000, knee_l.y * 1000, knee_l.z * 1000],
            "rightKnee_mm": [knee_r.x * 1000, knee_r.y * 1000, knee_r.z * 1000],
        },
        "display": {
            "eyeCenter_mm": [eye.x * 1000, eye.y * 1000, eye.z * 1000],
            "monitorCenter_mm": [monitor_x * 1000, monitor_y * 1000, monitor_center_z * 1000],
            "monitorTop_mm": monitor_top * 1000,
            "eyeMinusMonitorCenter_mm": (eye.z - monitor_center_z) * 1000,
            "eyeMinusMonitorTop_mm": (eye.z - monitor_top) * 1000,
            "viewDistanceY_mm": view_distance * 1000,
        },
        "clearance": {
            "deskUndersideProxy_mm": (desk_h - 0.04) * 1000,
            "leftKneeToDeskUndersideProxy_mm": (desk_h - 0.04 - knee_l.z) * 1000,
            "rightKneeToDeskUndersideProxy_mm": (desk_h - 0.04 - knee_r.z) * 1000,
        },
        "symmetry": symmetry,
        "validation": {"ok": validation_ok, "checks": checks},
        "assumptions": [
            "The seated avatar is a derived ergonomic reference pose, not a medical assessment.",
            "The rigid mesh does not model buttock or seat-cushion soft-tissue compression; seatSurfaceGapProxy is informational only.",
            "Desk, stool, display and input-device positions are the current Sweet Home 3D V1 measurements/placements.",
            "Monitor-arm geometry is omitted from ergonomic collision metrics; the monitor envelope is retained.",
        ],
    }

    for modifier in masks:
        modifier.show_viewport = True

    return report


def _write_report(report):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _build():
    body, rig, pose_targets = _create_pose()
    report = _report(body, rig, pose_targets)
    _write_report(report)

    bpy.ops.wm.save_as_mainfile(filepath=SEATED_PATH)
    bpy.ops.export_scene.gltf(
        filepath=GLB_PATH,
        export_format="GLB",
        use_selection=False,
        export_apply=False,
        export_all_influences=True,
    )

    return report


def _validate():
    if not os.path.isfile(SEATED_PATH):
        raise RuntimeError("seated scene does not exist; run build first")
    body = bpy.data.objects.get("PersonalTwinAvatar")
    rig = bpy.data.objects.get("PersonalTwinAvatar.SeatedRig")
    if body is None or rig is None:
        raise RuntimeError("saved seated scene is missing the body or seated rig")

    keyboard = _object_spec("keyboard")
    keyboard_width, keyboard_depth, keyboard_height = _dims_m(keyboard)
    keyboard_x, keyboard_y = _center_xy_m(keyboard)
    pose_targets = {
        "targetCrownZ_m": _m(_object_spec("stool")["height"]) + _m(_mm_measurement("sittingHeight")),
        "wristTarget": {
            "x_m": min(keyboard_width / 2, 0.18),
            "y_m": keyboard_y + keyboard_depth / 2 - 0.0125,
            "z_m": _m(keyboard["bottomZ"]) + keyboard_height - 0.004,
        },
    }
    report = _report(body, rig, pose_targets)
    _write_report(report)
    return report


report = _build() if ACTION == "build" else _validate()
print("PERSONAL_TWIN_RESULT=" + json.dumps(report, ensure_ascii=False, separators=(",", ":")))
if not report.get("validation", {}).get("ok", False):
    raise RuntimeError("seated ergonomics validation failed")
