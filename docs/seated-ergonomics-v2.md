# Seated ergonomics V2

The seated ergonomics layer is a derived view built from two private canonical inputs:

- the body measurement profile;
- the current desk/stool/display/input-device setup.

The measurement-fitted avatar remains the body-shape source. The seated scene is regenerated rather
than edited as an independent source of truth.

## Runtime outputs

The build command creates private runtime artifacts:

    runtime/data/ergonomics/avatar-seated.blend
    runtime/data/ergonomics/seated-report.json

The real desk setup stays under runtime/data/canonical/ergonomics and is ignored by Git.

## Commands

    scripts/ergonomics/seated-scene.sh build
    scripts/ergonomics/seated-scene.sh validate

build launches an isolated headless Blender process with the measurement-fitted avatar as its input, adds the
MPFB default rig, creates the seated pose and simplified ergonomic environment, writes the report,
and saves the derived Blender scene. The standalone seated GLB was retired; the Viewer consumes the
seated pose only through the integrated room + body scene.

validate launches another isolated Blender process from the saved seated scene and recomputes the
validation report. The measurement-fitted source avatar is never opened for writing.

## Coordinate convention

The ergonomic setup uses a local coordinate system with the floor under the stool center as the
origin. X points right, Z points up, and the desk is in negative Y. This avoids coupling ergonomic
calculations to Sweet Home 3D's room-global coordinates.

The private desk setup is currently a projection of the measured Sweet Home 3D furniture layout.
It can be regenerated later from a formal furniture projection without changing the pose layer.

## Pose contract

V2 uses:

- MPFB default rig;
- symmetric sagittal lower-body rotations;
- the fixed hm08 seat-support landmark aligned to the measured stool top;
- visible foot-floor contact as a validated constraint;
- symmetric wrist IK targets derived from the keyboard envelope;
- neutral upright torso.

The current morphology-aware avatar resolves the lower body at an implementation preset of
approximately 78 degrees hip flexion plus 80 degrees knee counter-rotation. A parameter sweep was
used to select this pair because it simultaneously keeps the rigid seat-contact proxy and the
visible feet within 1 mm of their measured support surfaces. These values are rig parameters, not
claimed clinical joint-angle measurements.

The canonical sitting-height measurement is still recorded in the report but is not used to
translate the body vertically while that private measurement is flagged for re-measurement.

## Validation

The build and validate commands check:

- seat-contact proxy against the measured stool top;
- visible body floor gap;
- left/right wrist height against the keyboard target;
- bilateral wrist and knee symmetry.

The report also records crown height, eye line, display geometry, desk clearance proxies and the
disputed canonical sitting-height value as non-enforced context.

A rigid surface mesh cannot reproduce buttock or cushion compression. The seat check therefore
uses a 10 mm contact tolerance and reports `seatSurfaceGapProxy`; it does not claim soft-tissue
accuracy. Crown height is now an output of the contact-driven pose instead of a hard target.

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

Keyboard/wrist alignment, seat contact, foot-floor gap and mouse-to-keyboard spacing use project heuristics only. They are marked separately in the report and are not represented as external standards. In particular, mouse placement in the V1 room model is approximate, so a mouse-reach finding is a prompt for confirmation rather than an automatic furniture change.

The Integrated Room + Body Viewer inspector is the single seated-ergonomics surface. It shows the overall reference-check count, desk-relative monitor envelope, modeled crown-to-monitor-top delta, monitor-height guidance and mouse-layout review values. The standalone proxy-furniture Seated Workstation view was retired because it duplicated the integrated scene and could diverge visually from the real room.

References:

- OSHA Computer Workstations - Monitors: https://www.osha.gov/etools/computer-workstations/components/monitors
- CCOHS Office Ergonomics - Positioning the Monitor: https://www.ccohs.ca/oshanswers/ergonomics/office/monitor_positioning.html
