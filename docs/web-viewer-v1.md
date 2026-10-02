# Personal Twin Web Viewer V1

The Web Viewer is a private, read-only inspection surface for derived Personal Twin assets. It is intentionally separate from SweetHome3DJS, which remains the room editor.

## Service

The Viewer is served on GCP dev port 21024 and exposed remotely only through Tailscale Serve.

The Docker image self-hosts Three.js 0.180.0 and its addons. The browser does not depend on a runtime CDN.

## Modes

The V1 UI exposes three modes:

1. Room — the current Sweet Home 3D room exported to OBJ, normalized to meters and converted to GLB.
2. Standing Body — the fitted neutral Body Twin exported from runtime/data/body/avatar.blend.
3. Seated Ergonomics — the derived seated workstation scene exported by the ergonomics pipeline.

The Viewer is not a source of truth. Canonical JSON remains authoritative for measurements and the authoring files remain authoritative for editable 3D state.

## Private runtime assets

Viewer source snapshots and generated outputs stay under ignored runtime paths:

    runtime/data/viewer/source/
    runtime/data/viewer/assets/

The expected generated assets are:

    room.glb
    room.json
    avatar-standing.glb
    avatar-standing.json
    avatar-seated.glb
    seated-v1-report.json
    body-summary.json
    manifest.json

The room source snapshot is an OBJ export of the current Sweet Home 3D scene. build-assets.sh converts Sweet Home 3D centimeters to meters, centers the plan footprint, and places the floor at zero before GLB export.

## Build assets

With the Blender workbench running:

    scripts/viewer/build-assets.sh

The command:

- exports the fitted neutral avatar to avatar-standing.glb;
- converts the private room OBJ snapshot to room.glb;
- copies the current seated ergonomics GLB and report into the Viewer asset set;
- derives a minimal private body-summary.json from canonical body facts for the inspector UI;
- emits manifest.json with SHA-256 and size metadata.

If the private room OBJ source is missing, the command leaves any existing room GLB untouched and warns rather than failing body asset generation.

## Viewer controls

- left mouse: orbit;
- wheel: zoom;
- right mouse: pan;
- keys 1 / 2 / 3: room / standing / seated;
- R: reset camera;
- direct URLs: `?mode=room`, `?mode=standing`, `?mode=seated`.

The camera is fitted from each loaded GLB bounding box, so no model-specific hard-coded camera coordinates are required.

`scripts/viewer/browser-smoke.sh` runs all three direct modes in Chromium under Xvfb and verifies that a Three.js canvas is created, the mode-specific inspector data is rendered and the loading state clears.

## Deployment

workbench-up.sh rebuilds Viewer assets after starting the Blender workbench, then starts the dedicated Nginx Viewer container. workbench-down.sh stops it with the other Personal Twin services.

The Viewer binds only to 127.0.0.1:21024 on the host. Tailscale Serve provides the private HTTPS endpoint.

## Current boundary

V1 switches between three independent derived views. It does not yet place the seated avatar into the full Sweet Home 3D room coordinate system. That requires a formal room-to-ergonomics transform so the combined scene remains measurement-driven rather than visually guessed.

The standing inspector intentionally reports both canonical height and the exported mesh height, plus their drift. Canonical body facts remain authoritative when the current fitted geometry and canonical measurements are not yet reconciled. The Viewer must expose that mismatch rather than silently presenting the mesh as an exact measurement model.
