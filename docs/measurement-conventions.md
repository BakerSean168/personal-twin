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
