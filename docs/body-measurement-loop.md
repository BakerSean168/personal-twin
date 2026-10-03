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

fit applies the private MPFB morphology configuration first, then re-fits standing height,
inseam, shoulder breadth, arm length, foot length, waist, hips and chest to the canonical
measurements. It updates the runtime reports and avatar-fit.json and saves avatar.blend only after
the full fit pass completes.

validate is read-only with respect to the Blender model and exits non-zero when a supported
canonical measurement is outside its tolerance.

Runtime body measurements remain ignored by Git.

## Morphology contract

Morphology is kept separate from manual body measurements. The private
`runtime/data/canonical/body/modeling.json` file controls the MPFB geometry macros that must be
reproducible when the avatar is rebuilt. Its public contract is
`schemas/body-modeling.schema.json`.

The MPFB `gender` value is explicitly a geometry parameter: 0 is the female-shaped endpoint and 1
is the male-shaped endpoint in MPFB's target interpolation. It is not an identity field. The
current fit also normalizes cup-size and firmness controls so stale female breast targets cannot
survive a morphology change.

Changing morphology invalidates the old measurement-target weights. The fit command therefore
re-solves all supported dimensions after applying the macro configuration instead of treating a
gender-slider change as an isolated cosmetic edit.

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

## Standing height

Standing height is measured from the visible MPFB body vertex group, not from all hm08 vertices.
The full base mesh also contains JointCubes and HelperGeometry whose extrema are not visible body
surface and previously inflated the height result.

The height solver normalizes the avatar's Z scale to the canonical standing height. Because the
morphology and leg-length targets can change vertical proportions, height and inseam are solved as
a coupled iterative pair before the remaining dimension targets are fitted.

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

## Waist and hips

Waist circumference is the central closed torso loop at the `joint-spine-3` centroid Z. Hip
circumference is the central closed torso loop at 40% of the vertical interval from
`joint-pelvis` to `joint-spine-4`. These planes are topology/skeleton anchored so the measurement
does not drift with world-space height scaling.

The fit uses MPFB's `measure-waist-circ-*` and `measure-hips-circ-*` targets and binary-searches
their legal 0..1 weights.

## Inseam

Structural inseam is defined as:

    crotch landmark Z - joint-ground centroid Z

This intentionally does not use hip-joint height. The crotch anchor sits on the fixed medial
upper-leg topology. The V3 fit adjusts upper- and lower-leg height targets together, preserving a
balanced leg-length change, and couples this with the standing-height solver.

## Sitting height

V1 uses a structural neutral-pose proxy:

    crown Z - seat-support landmark Z

The seat-support pair is on the bilateral inferior/posterior buttock surface. This neutral-pose
value is retained as a structural proxy only. The seated V2 contact-driven pose does not enforce
canonical sitting height while that private measurement is flagged for re-measurement; vertical
placement is instead anchored by seat contact and validated foot-floor contact. Sitting height is
therefore not part of standing-body validation and remains contextual evidence in the seated report.

## Current V3 fitting policy

The morphology-aware fit directly solves:

- visible standing height;
- shoulder breadth;
- arm length;
- average foot length;
- waist circumference;
- hip circumference;
- chest circumference;
- inseam.

Every supported dimension is re-measured after fitting and must pass its tolerance before the
result is accepted. Weight remains a canonical fact but is not mapped to MPFB's abstract weight
macro because a kg-to-slider calibration has not been defined.

Sitting height remains a canonical fact whose operational validation belongs to the seated
ergonomics layer. Its current private measurement is explicitly flagged for re-measurement, so it
must not drive furniture changes until that conflict is resolved.

Canonical measurements remain the source of truth even when a mesh measurement is within
tolerance.
