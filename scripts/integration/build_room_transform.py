#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROOM_META = ROOT / "runtime/data/viewer/assets/room.json"
SETUP = ROOT / "runtime/data/canonical/ergonomics/desk-setup.json"
ANCHOR = ROOT / "runtime/data/canonical/ergonomics/room-anchor.json"
OUT = ROOT / "runtime/data/viewer/assets/room-integration.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require_close(label: str, actual: float, expected: float, tolerance: float = 1e-6) -> None:
    if abs(actual - expected) > tolerance:
        raise RuntimeError(
            f"{label} mismatch: actual={actual:.9f} expected={expected:.9f} "
            f"error={actual - expected:.9f}"
        )


room = load(ROOM_META)
setup = load(SETUP)
anchor = load(ANCHOR)

bounds_min = room["sourceBounds"]["min"]
bounds_max = room["sourceBounds"]["max"]
center_x = (bounds_min[0] + bounds_max[0]) / 2
center_y = (bounds_min[1] + bounds_max[1]) / 2
normalization_offset = [-center_x, -center_y, -bounds_min[2]]

stool = anchor["anchors"]["stool"]
desk = anchor["anchors"]["desk"]


def sh3d_to_room(x_cm: float, y_cm: float, z_cm: float = 0.0) -> list[float]:
    """Convert Sweet Home 3D plan coordinates into normalized room-viewer meters."""
    return [
        x_cm / 100.0 + normalization_offset[0],
        -y_cm / 100.0 + normalization_offset[1],
        z_cm / 100.0 + normalization_offset[2],
    ]


stool_room = sh3d_to_room(stool["xCm"], stool["yCm"], stool["elevationCm"])
desk_room = sh3d_to_room(desk["xCm"], desk["yCm"], desk["elevationCm"])

# Ergonomics local coordinates are anchored at stool center and follow the SH3D
# plan X/Y directions. The OBJ/Blender room frame flips SH3D plan Y.
matrix = [
    [1.0, 0.0, 0.0, stool_room[0]],
    [0.0, -1.0, 0.0, stool_room[1]],
    [0.0, 0.0, 1.0, stool_room[2]],
    [0.0, 0.0, 0.0, 1.0],
]


def transform(local_xyz_m: list[float]) -> list[float]:
    x, y, z = local_xyz_m
    return [
        x + stool_room[0],
        -y + stool_room[1],
        z + stool_room[2],
    ]


setup_stool = setup["objects"]["stool"]["center"]
require_close("setup stool x", float(setup_stool["x"]), 0.0)
require_close("setup stool y", float(setup_stool["y"]), 0.0)

setup_desk = setup["objects"]["desk"]["center"]
setup_desk_local_m = [
    float(setup_desk["x"]) / 1000.0,
    float(setup_desk["y"]) / 1000.0,
    0.0,
]
predicted_desk_room = transform(setup_desk_local_m)

desk_local_from_sh3d_mm = [
    (desk["xCm"] - stool["xCm"]) * 10.0,
    (desk["yCm"] - stool["yCm"]) * 10.0,
]
desk_local_residual_mm = [
    desk_local_from_sh3d_mm[0] - float(setup_desk["x"]),
    desk_local_from_sh3d_mm[1] - float(setup_desk["y"]),
]
desk_room_residual_mm = [
    (predicted_desk_room[i] - desk_room[i]) * 1000.0 for i in range(3)
]

if max(abs(v) for v in desk_local_residual_mm + desk_room_residual_mm) > 0.5:
    raise RuntimeError(
        "room/ergonomics anchor residual exceeds 0.5 mm: "
        f"local={desk_local_residual_mm}, room={desk_room_residual_mm}"
    )

payload = {
    "schemaVersion": 1,
    "kind": "ergonomics-to-room-transform",
    "source": {
        "room": str(ROOM_META.relative_to(ROOT)),
        "ergonomicsSetup": str(SETUP.relative_to(ROOT)),
        "roomAnchor": str(ANCHOR.relative_to(ROOT)),
    },
    "coordinateSystems": {
        "ergonomics": {
            "unit": "m",
            "origin": "stool_center_floor",
            "axes": {"x": "plan-right", "y": "sh3d-plan-down", "z": "up"},
        },
        "roomViewer": {
            "unit": "m",
            "origin": "normalized-room-bounds-center-floor",
            "axes": {"x": "sh3d-plan-right", "y": "negative-sh3d-plan-down", "z": "up"},
        },
    },
    "roomNormalizationOffset_m": normalization_offset,
    "stoolRoom_m": stool_room,
    "deskRoom_m": desk_room,
    "matrixRowMajor": matrix,
    "linearDeterminant": -1.0,
    "handednessConversion": "flip-y",
    "validation": {
        "ok": True,
        "deskLocalResidual_mm": desk_local_residual_mm,
        "deskRoomResidual_mm": desk_room_residual_mm,
        "tolerance_mm": 0.5,
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
