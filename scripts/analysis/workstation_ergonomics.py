#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEATED_REPORT = ROOT / "runtime/data/ergonomics/seated-report.json"
DESK_SETUP = ROOT / "runtime/data/canonical/ergonomics/desk-setup.json"
OUT = ROOT / "runtime/data/viewer/assets/workstation-analysis.json"

OSHA_MONITOR_URL = "https://www.osha.gov/etools/computer-workstations/components/monitors"
CCOHS_MONITOR_URL = "https://www.ccohs.ca/oshanswers/ergonomics/office/monitor_positioning.html"

REFERENCE = {
    "monitorViewingDistance_mm": {"min": 500.0, "max": 1000.0},
    "monitorCenterDownAngle_deg": {"min": 15.0, "max": 20.0},
    "monitorTopAboveEye_mm": {"max": 0.0},
    "monitorLateralAngle_deg": {"max": 35.0},
}

# These are implementation heuristics for layout review, not external standards.
HEURISTICS = {
    "keyboardWristVerticalError_mm": {"max": 15.0},
    "mouseKeyboardEdgeGap_mm": {"preferredMax": 100.0},
    "feetFloorAbsGap_mm": {"max": 10.0},
    "seatContactAbsGap_mm": {"max": 10.0},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def in_range(value: float, *, minimum: float | None = None, maximum: float | None = None) -> bool:
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


seated = load(SEATED_REPORT)
setup = load(DESK_SETUP)

display = seated["display"]
geometry = seated["geometry"]
clearance = seated["clearance"]
objects = setup["objects"]

eye_x, eye_y, eye_z = [float(v) for v in display["eyeCenter_mm"]]
monitor_x, monitor_y, monitor_z = [float(v) for v in display["monitorCenter_mm"]]
monitor_top = float(display["monitorTop_mm"])

dx = monitor_x - eye_x
dy = monitor_y - eye_y
plan_distance = math.hypot(dx, dy)
vertical_drop = eye_z - monitor_z
center_down_angle = math.degrees(math.atan2(vertical_drop, plan_distance))
lateral_angle = math.degrees(math.atan2(abs(dx), abs(dy))) if abs(dy) > 1e-9 else 90.0
top_above_eye = monitor_top - eye_z

target_drop_15 = math.tan(math.radians(REFERENCE["monitorCenterDownAngle_deg"]["min"])) * plan_distance
lower_for_15 = max(0.0, target_drop_15 - vertical_drop)
lower_for_top = max(0.0, top_above_eye)
suggested_monitor_lowering = max(lower_for_15, lower_for_top)

desk = objects["desk"]
monitor = objects["monitor"]
keyboard = objects["keyboard"]
mouse = objects["mouse"]

desk_top = float(desk["height"])
monitor_bottom = float(monitor["bottomZ"])
monitor_height = float(monitor["height"])
monitor_top_abs = monitor_bottom + monitor_height
monitor_bottom_above_desk = monitor_bottom - desk_top
monitor_top_above_desk = monitor_top_abs - desk_top
crown_minus_monitor_top = float(geometry["crownHeight_mm"]) - monitor_top_abs

monitor_override = ((setup.get("source") or {}).get("manualMeasurements") or {}).get("monitorVertical")
if monitor_override:
    expected_bottom = float(monitor_override["bottomAboveDesk_mm"])
    expected_top = float(monitor_override["topAboveDesk_mm"])
    if abs(monitor_bottom_above_desk - expected_bottom) > 1.0:
        raise RuntimeError("monitor bottom does not match the manual desk-relative measurement")
    if abs(monitor_top_above_desk - expected_top) > 1.0:
        raise RuntimeError("monitor top does not match the manual desk-relative measurement")

keyboard_top = float(keyboard["bottomZ"]) + float(keyboard["height"])
left_wrist_z = float(geometry["leftWrist_mm"][2])
right_wrist_z = float(geometry["rightWrist_mm"][2])
mean_wrist_z = (left_wrist_z + right_wrist_z) / 2.0
keyboard_wrist_error = mean_wrist_z - keyboard_top

keyboard_right_edge = float(keyboard["center"]["x"]) + float(keyboard["width"]) / 2.0
mouse_left_edge = float(mouse["center"]["x"]) - float(mouse["width"]) / 2.0
mouse_keyboard_gap = max(0.0, mouse_left_edge - keyboard_right_edge)
mouse_move_inward = max(
    0.0,
    mouse_keyboard_gap - HEURISTICS["mouseKeyboardEdgeGap_mm"]["preferredMax"],
)

checks = {
    "monitorViewingDistance": {
        "value": plan_distance,
        "unit": "mm",
        "status": "ok"
        if in_range(
            plan_distance,
            minimum=REFERENCE["monitorViewingDistance_mm"]["min"],
            maximum=REFERENCE["monitorViewingDistance_mm"]["max"],
        )
        else "review",
        "reference": REFERENCE["monitorViewingDistance_mm"],
    },
    "monitorCenterDownAngle": {
        "value": center_down_angle,
        "unit": "deg",
        "status": "ok"
        if in_range(
            center_down_angle,
            minimum=REFERENCE["monitorCenterDownAngle_deg"]["min"],
            maximum=REFERENCE["monitorCenterDownAngle_deg"]["max"],
        )
        else "review",
        "reference": REFERENCE["monitorCenterDownAngle_deg"],
    },
    "monitorTopRelativeToEye": {
        "value": top_above_eye,
        "unit": "mm",
        "status": "ok"
        if in_range(top_above_eye, maximum=REFERENCE["monitorTopAboveEye_mm"]["max"])
        else "review",
        "reference": REFERENCE["monitorTopAboveEye_mm"],
    },
    "monitorLateralAngle": {
        "value": lateral_angle,
        "unit": "deg",
        "status": "ok"
        if in_range(lateral_angle, maximum=REFERENCE["monitorLateralAngle_deg"]["max"])
        else "review",
        "reference": REFERENCE["monitorLateralAngle_deg"],
    },
    "keyboardWristVerticalAlignment": {
        "value": keyboard_wrist_error,
        "unit": "mm",
        "status": "ok"
        if abs(keyboard_wrist_error) <= HEURISTICS["keyboardWristVerticalError_mm"]["max"]
        else "review",
        "heuristic": HEURISTICS["keyboardWristVerticalError_mm"],
    },
    "feetFloorContact": {
        "value": float(geometry["footFloorGap_mm"]),
        "unit": "mm",
        "status": "ok"
        if abs(float(geometry["footFloorGap_mm"])) <= HEURISTICS["feetFloorAbsGap_mm"]["max"]
        else "review",
        "heuristic": HEURISTICS["feetFloorAbsGap_mm"],
    },
    "seatContact": {
        "value": float(geometry["seatSurfaceGapProxy_mm"]),
        "unit": "mm",
        "status": "ok"
        if abs(float(geometry["seatSurfaceGapProxy_mm"])) <= HEURISTICS["seatContactAbsGap_mm"]["max"]
        else "review",
        "heuristic": HEURISTICS["seatContactAbsGap_mm"],
    },
    "mouseKeyboardEdgeGap": {
        "value": mouse_keyboard_gap,
        "unit": "mm",
        "status": "ok"
        if mouse_keyboard_gap <= HEURISTICS["mouseKeyboardEdgeGap_mm"]["preferredMax"]
        else "review",
        "heuristic": HEURISTICS["mouseKeyboardEdgeGap_mm"],
        "confidence": "layout-approximation",
    },
}

findings = []
if checks["monitorCenterDownAngle"]["status"] != "ok" or checks["monitorTopRelativeToEye"]["status"] != "ok":
    findings.append(
        {
            "id": "monitor-height",
            "priority": 1,
            "status": "review",
            "message": (
                "The modeled seated eye line places the monitor above the reference band, "
                "but the private sitting-height/posture measurement is still under re-check. "
                "Do not change the physical monitor from this model alone."
            ),
            "suggestedAdjustment": {
                "action": "defer-monitor-adjustment",
                "amount_mm": suggested_monitor_lowering,
                "basis": (
                    "modeled amount to reach at least 15 deg downward center gaze while keeping "
                    "screen top at/below eye level; retain as diagnostic evidence until seated "
                    "eye/crown height is re-measured"
                ),
                "apply": False,
            },
        }
    )

if checks["mouseKeyboardEdgeGap"]["status"] != "ok":
    findings.append(
        {
            "id": "mouse-reach",
            "priority": 2,
            "status": "review",
            "message": "Modeled mouse position is separated from the keyboard by a large lateral gap.",
            "suggestedAdjustment": {
                "action": "move-mouse-inward",
                "amount_mm": mouse_move_inward,
                "basis": "project layout heuristic; verify the approximate mouse placement before changing furniture",
            },
        }
    )

ok_count = sum(1 for item in checks.values() if item["status"] == "ok")
review_count = len(checks) - ok_count

payload = {
    "schemaVersion": 1,
    "kind": "workstation-ergonomics-analysis",
    "setupId": setup["setupId"],
    "poseVersion": seated["poseVersion"],
    "references": [
        {
            "name": "OSHA Computer Workstations - Monitors",
            "url": OSHA_MONITOR_URL,
            "usedFor": [
                "viewing distance 500-1000 mm",
                "screen top at/below eye level",
                "screen center 15-20 deg below horizontal eye level",
                "monitor lateral angle not beyond 35 deg",
            ],
        },
        {
            "name": "CCOHS Office Ergonomics - Positioning the Monitor",
            "url": CCOHS_MONITOR_URL,
            "usedFor": ["cross-check of downward viewing angle and viewing distance guidance"],
        },
    ],
    "checks": checks,
    "derived": {
        "monitorPlanDistance_mm": plan_distance,
        "monitorCenterDownAngle_deg": center_down_angle,
        "monitorLateralAngle_deg": lateral_angle,
        "monitorTopAboveEye_mm": top_above_eye,
        "suggestedMonitorLowering_mm": suggested_monitor_lowering,
        "keyboardTop_mm": keyboard_top,
        "meanWristHeight_mm": mean_wrist_z,
        "keyboardWristVerticalError_mm": keyboard_wrist_error,
        "mouseKeyboardEdgeGap_mm": mouse_keyboard_gap,
        "suggestedMouseMoveInward_mm": mouse_move_inward,
        "monitorBottomAboveDesk_mm": monitor_bottom_above_desk,
        "monitorTopAboveDesk_mm": monitor_top_above_desk,
        "crownMinusMonitorTop_mm": crown_minus_monitor_top,
        "leftKneeClearanceProxy_mm": float(clearance["leftKneeToDeskUndersideProxy_mm"]),
        "rightKneeClearanceProxy_mm": float(clearance["rightKneeToDeskUndersideProxy_mm"]),
        "seatToDeskTop_mm": float(geometry["seatToDeskTop_mm"]),
    },
    "summary": {
        "okChecks": ok_count,
        "reviewChecks": review_count,
        "priorityFindingCount": len(findings),
    },
    "findings": sorted(findings, key=lambda item: item["priority"]),
    "assumptions": [
        "This is a workstation layout reference analysis, not a medical diagnosis.",
        "The seated pose is a rigid-body approximation; vertical placement uses seat/floor contact and does not enforce the disputed sitting-height measurement.",
        "The rigid mesh does not model soft-tissue compression at the seat contact.",
        "Mouse placement in the V1 room model is approximate; mouse-reach findings require visual confirmation.",
        "External ergonomic ranges are reference guidance, not absolute pass/fail safety limits.",
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
