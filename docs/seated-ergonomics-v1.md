# Seated ergonomics V1

The seated ergonomics layer is a derived view built from two private canonical inputs:

- the body measurement profile;
- the current desk/stool/display/input-device setup.

The neutral fitted avatar remains the body-shape source. The seated scene is regenerated rather
than edited as an independent source of truth.

## Runtime outputs

The build command creates private runtime artifacts:

    runtime/data/ergonomics/avatar-seated.blend
    runtime/data/ergonomics/avatar-seated.glb
    runtime/data/ergonomics/seated-v1-report.json

The real desk setup stays under runtime/data/canonical/ergonomics and is ignored by Git.

## Commands

    scripts/ergonomics/seated-scene.sh build
    scripts/ergonomics/seated-scene.sh validate

build launches an isolated headless Blender process with the neutral avatar as its input, adds the
MPFB default rig, creates the seated pose and simplified ergonomic environment, writes the report,
saves the derived Blender scene, and exports GLB.

validate launches another isolated Blender process from the saved seated scene and recomputes the
validation report. The neutral avatar is never opened for writing.

## Coordinate convention

The ergonomic setup uses a local coordinate system with the floor under the stool center as the
origin. X points right, Z points up, and the desk is in negative Y. This avoids coupling ergonomic
calculations to Sweet Home 3D's room-global coordinates.

The private desk setup is currently a projection of the measured Sweet Home 3D furniture layout.
It can be regenerated later from a formal furniture projection without changing the pose layer.

## Pose contract

V1 uses:

- MPFB default rig;
- symmetric sagittal lower-body rotations;
- a canonical sitting-height constraint for the crown;
- floor contact as the foot constraint;
- symmetric wrist IK targets derived from the keyboard envelope;
- neutral upright torso.

The current fitted avatar resolves the lower body at approximately 72 degrees hip flexion preset
plus the corresponding 72 degree knee counter-rotation. These are implementation pose parameters,
not claimed clinical joint-angle measurements.

## Validation

The build and validate commands check:

- crown height against stool height plus canonical sitting height;
- body floor gap;
- left/right wrist height against the keyboard target;
- bilateral wrist and knee symmetry.

The report also records display geometry and desk clearance proxies.

Seat contact is intentionally informational in V1. A rigid surface mesh cannot reproduce buttock
or cushion compression. The report therefore exposes seatSurfaceGapProxy rather than deforming the
body solely to force visual contact and thereby corrupting the measured sitting-height constraint.

## Interpretation boundary

This layer is for spatial and ergonomic reasoning. It is not a medical or biomechanical diagnosis,
and its current simplified desk/stool/monitor meshes are measurement envelopes rather than
photorealistic furniture models.

## Derived workstation analysis

`scripts/analysis/workstation_ergonomics.py` consumes the seated report and the private desk setup and writes a derived `workstation-analysis.json` for the Viewer. It does not modify canonical measurements or furniture placement.

The external reference checks use public workstation guidance from OSHA and CCOHS for monitor placement. The current reference bands are:

- eye-to-screen viewing distance: 500-1000 mm;
- monitor top at or below eye level;
- monitor center approximately 15-20 degrees below horizontal eye level;
- monitor lateral angle no farther than 35 degrees from straight ahead.

Keyboard/wrist alignment, foot-floor gap and mouse-to-keyboard spacing use project heuristics only. They are marked separately in the report and are not represented as external standards. In particular, mouse placement in the V1 room model is approximate, so a mouse-reach finding is a prompt for confirmation rather than an automatic furniture change.

The Seated Workstation Viewer inspector surfaces this distinction directly. It shows the overall reference-check count, a monitor-height adjustment only when the derived analysis contains a monitor-height finding, and a mouse inward-move suggestion only as a modeled value marked `待确认`. If `workstation-analysis.json` is unavailable, the inspector degrades to the raw seated geometry metrics instead of inventing recommendations.

References:

- OSHA Computer Workstations - Monitors: https://www.osha.gov/etools/computer-workstations/components/monitors
- CCOHS Office Ergonomics - Positioning the Monitor: https://www.ccohs.ca/oshanswers/ergonomics/office/monitor_positioning.html
