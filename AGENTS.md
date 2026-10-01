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

## Runtime workbench and MCP

On GCP dev, V1 uses these entry points:

- native SweetHome3DJS editor: `http://127.0.0.1:21020`
- Sweet Home 3D MCP: `http://127.0.0.1:21021/mcp` (Streamable HTTP)
- Blender MCP: `http://127.0.0.1:21022/sse` (SSE)
- Personal Twin Memory MCP: `http://127.0.0.1:21023/mcp` (Streamable HTTP)
- maintenance Webtop: `http://127.0.0.1:21029`

Actual private runtime data lives under `runtime/` and is ignored by Git. Read `runtime/data/canonical/` for factual measurements. Store durable AI notes under `runtime/data/memory/` through Personal Twin Memory MCP; notes never override canonical facts. Human room editing should use SweetHome3DJS on port 21020. Before AI room mutations, run `scripts/space-sync-from-web.sh` so the desktop/MCP model reloads the newest web-edited `.sh3x`; after AI saves the desktop model, run `scripts/space-sync-to-web.sh` to refresh the browser-readable `.sh3x`. On service startup, `scripts/space-reconcile.sh` compares both files and converts the newer one to the older format before either editor is started. Use Blender MCP for body/avatar or general 3D scene operations.

Do not replace SweetHome3DJS, Sweet Home 3D, MPFB or Blender with custom editors unless the user explicitly changes the product direction.
