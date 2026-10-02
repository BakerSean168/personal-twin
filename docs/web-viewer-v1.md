# Personal Twin Web Viewer V1

The Web Viewer is a private, read-only inspection surface for derived Personal Twin assets. It is intentionally separate from SweetHome3DJS, which remains the room editor.

## Service

The Viewer is served on GCP dev port 21024 and exposed remotely only through Tailscale Serve.

The Docker image self-hosts Three.js 0.180.0 and its addons. The browser does not depend on a runtime CDN.

## Modes

The V1 UI exposes four modes:

1. Room — the current Sweet Home 3D room exported to OBJ, normalized to meters and converted to GLB.
2. Integrated Room + Body — the real room plus the seated Body Twin transformed into the Sweet Home 3D furniture frame.
3. Standing Body — the fitted neutral Body Twin exported from runtime/data/body/avatar.blend.
4. Seated Ergonomics — the standalone derived seated workstation scene exported by the ergonomics pipeline.

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
    room-integration.json
    scene-combined.glb
    scene-combined.json
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
- validates the private Sweet Home 3D stool/desk anchors against the ergonomics setup;
- builds a formal ergonomics-to-room transform and a combined room + seated-body GLB;
- emits manifest.json with SHA-256 and size metadata.

If the private room OBJ source is missing, the command leaves any existing room GLB untouched and warns rather than failing body asset generation.

## Viewer controls

- left mouse: orbit;
- wheel: zoom;
- right mouse: pan;
- keys 1 / 2 / 3 / 4: room / combined / standing / seated;
- R: reset camera;
- direct URLs: `?mode=room`, `?mode=combined`, `?mode=standing`, `?mode=seated`.

The camera is fitted from each loaded GLB bounding box, so no model-specific hard-coded camera coordinates are required.

`scripts/viewer/browser-smoke.sh` runs all four direct modes in Chromium under Xvfb and verifies that a Three.js canvas is created, the mode-specific inspector data is rendered and the loading state clears.

## Deployment

workbench-up.sh rebuilds Viewer assets after starting the Blender workbench, then starts the dedicated Nginx Viewer container. workbench-down.sh stops it with the other Personal Twin services.

The Viewer binds only to 127.0.0.1:21024 on the host. Tailscale Serve provides the private HTTPS endpoint.

## Room / ergonomics transform

The combined view is measurement-driven rather than visually aligned by eye. A private room anchor records the Sweet Home 3D stool and desk centers from Home.xml. The integration step validates that their relative displacement matches the canonical ergonomics setup, then maps the stool-centered ergonomics frame into the normalized room GLB frame.

Sweet Home 3D plan Y and OBJ/Blender Y point in opposite directions, so this coordinate conversion contains a Y handedness flip. The seated body is baked from the validated avatar-seated.blend pose into the target frame and its face winding is reversed during the conversion so normals remain outward.

The standing inspector reports canonical height, exported visible-mesh height and their drift. The current height-normalized Body V2 is expected to keep this drift near zero. The metric remains visible so a future fitting regression is exposed immediately instead of being hidden by stale metadata.

## Current boundary

The integrated V1 scene uses the current room snapshot and seated pose as static derived assets. It does not yet make the body interactively draggable inside SweetHome3DJS, and it intentionally does not turn the combined GLB into another source of truth.
