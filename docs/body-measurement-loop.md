# Body measurement loop

Body Twin keeps manual measurements as canonical facts and treats the MPFB mesh as a derived view.
The measurement loop answers a narrower question: does the current derived avatar still match the
canonical dimensions that can be measured reproducibly from MPFB's fixed hm08 topology?

## Commands

With the workbench running:

    scripts/body/body-model.sh measure
    scripts/body/body-model.sh fit
    scripts/body/body-model.sh validate

measure is read-only with respect to the Blender model. It writes private runtime reports to
runtime/data/body/body-measurements.json and runtime/data/body/landmarks.json.

fit currently fits chest circumference through the MPFB bust-circumference target, updates the
runtime reports and avatar-fit.json, and saves avatar.blend.

validate is read-only with respect to the Blender model and exits non-zero when a supported
canonical measurement is outside its tolerance.

Runtime body measurements remain ignored by Git.

## Stable landmarks

The V1 landmark contract targets the MPFB hm08 base topology.

| Landmark | Definition | Use |
| --- | --- | --- |
| Crown | fixed vertex 881 | top reference for sitting height |
| Crotch | mean of 4425, 11043, 6395, 12992 | upper reference for inseam |
| Seat plane | bilateral mean of 4455, 11073 | lower reference for structural sitting height |
| Ground | centroid of joint-ground vertex group | lower reference for inseam |
| Chest plane | Z of nippleTip centroid, falling back to nipple | plane for chest circumference |

The implementation verifies symmetry and anatomical placement before using fixed-topology
landmarks. A future incompatible MPFB topology must therefore fail rather than silently produce a
different measurement.

## Chest circumference

The old prototype used a convex hull at an arbitrary Z plane. A convex hull can bridge the torso
and arms, inflating circumference.

V1 instead:

1. derives the chest plane from the MPFB nipple landmark;
2. intersects body triangles with that plane;
3. stitches intersection segments into closed loops;
4. selects the central largest-area loop as the torso;
5. keeps left and right arm loops separate;
6. measures the actual torso-loop perimeter.

The fit step chooses measure-bust-circ-decr or measure-bust-circ-incr and binary-searches the
shape-key weight until the torso loop matches the canonical chest circumference.

## Inseam

Structural inseam is defined as:

    crotch landmark Z - joint-ground centroid Z

This intentionally does not use hip-joint height. The crotch anchor sits on the fixed medial
upper-leg topology.

## Sitting height

V1 uses a structural neutral-pose proxy:

    crown Z - seat-support landmark Z

The seat-support pair is on the bilateral inferior/posterior buttock surface. This is a body
proportion metric. A future seated-pose ergonomics layer may add a compressed seat-contact
measurement, but it should remain a separate metric rather than changing this definition.

## Current V1 fitting policy

Chest circumference is directly fitted.

Inseam and sitting height now have stable landmarks and are validated against canonical values.
They are not actively fitted yet because V1 does not have a calibrated proof that the relevant
MPFB leg/torso targets change only those dimensions without degrading already accepted
measurements.

Canonical measurements remain the source of truth even when a mesh measurement is within
tolerance.
