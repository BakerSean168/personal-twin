# Measurement conventions

## General

- Store lengths in millimetres (mm).
- Store mass in kilograms (kg).
- Store the original measured value; convert only at UI/import boundaries.
- Record provenance where it affects interpretation.
- Keep left/right values separate when asymmetry is possible.

## Body provenance

- manual_tape
- device_scan
- imported
- mesh
- inferred
- unknown

V1 stores one selected observation per field. A later schema may add observation history.

## Space

V1 assumes a rectangular room.

Coordinate system:

- origin = south-west floor corner
- +X = east
- +Y = north
- +Z = up

Openings are anchored to a named wall and an offset from that wall's start.

## Furniture

Furniture dimensions describe the physical bounding size. Clearance is a semantic operating zone, such as chair pull-back, drawer access or wardrobe door access.

## Derived body measurement loop

Canonical body measurements remain manual/device observations. Measurements read back from an MPFB
mesh are derived verification data and must not overwrite canonical facts.

Chest circumference is measured from the closed central torso intersection loop at the nipple
landmark height. Inseam uses the fixed crotch topology landmark relative to the ground reference.
Structural sitting height uses the crown landmark relative to the bilateral seat-support landmark.

The exact landmark contract and supported tolerances are documented in
docs/body-measurement-loop.md.
