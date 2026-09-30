# AGENTS.md

## Project intent

personal-twin is an open, AI-friendly personal digital-twin data and asset repository. It is not initially a web application.

## Source-of-truth hierarchy

1. Canonical measurement JSON.
2. Editor source files (.sh3d, .blend, .mhm) derived from or reconciled with canonical measurements.
3. Web/export files (.glb, .gltf, renders) are derived artifacts.

Never infer canonical measurements from a mesh when explicit measurements are available.

## Privacy boundary

The GitHub repository is public.

- Never add files from data/private/ or source/private/ to Git.
- Never move private measurements into examples without explicit user instruction.
- Do not commit room photos, scans, precise residence details or personal body scans by default.
- Public examples must remain synthetic or intentionally sanitized.

## Units and coordinates

- Length: millimetres (mm)
- Mass: kilograms (kg)
- Space origin: floor-level south-west corner
- X: east
- Y: north
- Z: up
- Rotations: degrees around +Z unless an adapter states otherwise

## Editing rules

- Change schemas deliberately; increment schemaVersion for breaking contract changes.
- Update examples and validation with schema changes.
- Preserve provenance for body measurements.
- Keep editor-specific metadata out of canonical schemas.
- Prefer deterministic scripts for exports and transformations.

## Verification

    python3 scripts/validate_json.py
