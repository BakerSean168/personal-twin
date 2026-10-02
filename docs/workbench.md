# Personal Twin Web Workbench

V1 deliberately reuses mature native editors instead of implementing a custom 3D editor.

## Components

- SweetHome3DJS 7.5.2: native browser/WebGL room, wall, opening and furniture editing.
- Sweet Home 3D 7.5 + Sweet Home 3D MCP 1.1.0: AI-side room scene engine and maintenance editor.
- Blender 5.1.2 + MPFB 2.0.17: body/avatar generation and advanced 3D work.
- Blender MCP 1.0.0: AI inspection and scene editing.
- Personal Twin Memory MCP: durable private AI notes plus read-only access to canonical JSON.
- Personal Twin Viewer: self-hosted Three.js read-only viewer for room, integrated room + body, standing Body Twin and seated ergonomics GLB assets.
- LinuxServer Webtop: maintenance/debug access to the native desktop applications only.
- Tailscale Serve: private HTTPS ingress for the native editor, Twin Viewer, maintenance Webtop and MCP endpoints.

## Runtime

The runtime is intentionally ignored by Git:

- `runtime/data/canonical/`: canonical private JSON.
- `runtime/data/spaces/`: Sweet Home 3D source files.
- `runtime/data/body/`: Blender/MPFB body source files.
- `runtime/data/ergonomics/`: seated workstation derived scenes and reports.
- `runtime/data/viewer/`: private Viewer source snapshots and generated GLB assets.
- `runtime/data/exports/`: other derived web/export assets.
- `runtime/data/memory/`: durable AI memory records, separate from canonical facts.
- `runtime/data/mcp/servers.json`: actual local/tailnet MCP endpoints.
- `runtime/workbench/config/`: persistent editor preferences and installed extensions.

The public repository contains only code, schemas, documentation and sanitized examples.

## Ports on GCP dev

| Port | Service |
| --- | --- |
| 21020 | SweetHome3DJS native WebGL editor |
| 21021 | Sweet Home 3D MCP (Streamable HTTP `/mcp`) |
| 21022 | Blender MCP (SSE `/sse`) |
| 21023 | Personal Twin Memory MCP (Streamable HTTP `/mcp`) |
| 21024 | Personal Twin Three.js Viewer |
| 21029 | Maintenance Webtop (Sweet Home 3D desktop + Blender/MPFB) |

All host ports bind to loopback. Remote access is provided through Tailscale Serve only.

## Start

Run `./scripts/workbench-up.sh`.

The start script builds the maintenance workbench and converter, temporarily stops both editor surfaces, reconciles `.sh3d` and `.sh3x` by modification time (newest wins), then starts the desktop/MCP engine and SweetHome3DJS on port 21020. It rebuilds the private Viewer assets from the neutral body, current room OBJ snapshot and seated ergonomics outputs, then starts the Three.js Viewer on port 21024. Tailscale Serve exposes the native editor, Viewer, maintenance Webtop and all three MCP services. It also regenerates `runtime/data/mcp/servers.json` from fixed local ports and the current node DNS name, so local and tailnet endpoints cannot silently drift. The public repository intentionally does not hardcode the private tailnet hostname.

Normal room editing should happen in SweetHome3DJS on port 21020, where rendering runs in the user's browser. Twin Viewer on port 21024 is read-only and is the normal inspection surface for room, integrated room + body, standing body and seated ergonomics views. Webtop on port 21029 is retained only for Blender/MPFB and maintenance/debug tasks.

## Verify

Run `./scripts/workbench-smoke.sh`.

The smoke test verifies the native SweetHome3DJS page, the `bedroom.sh3x` home list and `Home.xml` archive entry, the Twin Viewer page plus its required GLB/report/cutaway assets, and all four Viewer modes with an opt-in framebuffer render probe so an empty 3D viewport cannot pass. It also verifies maintenance Webtop, the generated three-service MCP registry, active Tailscale Serve entries, required source assets, and a create/read/list/delete round trip through Personal Twin Memory MCP. Reversible editor write checks remain in place: Sweet Home 3D creates a temporary label behind a checkpoint and restores the checkpoint, while Blender creates and removes a temporary scene object through `execute_blender_code`.

## Current V1 seed

The local runtime seeds the first private room from canonical JSON. Exact residential dimensions remain in ignored runtime/private data and are not committed to this public repository. The AI/desktop source is `runtime/data/spaces/bedroom/bedroom.sh3d`; the browser source is `runtime/data/spaces/bedroom/bedroom.sh3x`. `scripts/space-reconcile.sh` resolves restart-time drift, while `scripts/space-sync-from-web.sh` and `scripts/space-sync-to-web.sh` perform explicit live handoffs between the two official Sweet Home 3D formats. Writes use a temporary output and atomic rename so a failed conversion cannot truncate the current room file.

The body asset at `runtime/data/body/avatar.blend` is the private neutral Body Twin derived from canonical measurements. Seated ergonomics is a separate derived scene and does not overwrite the neutral body. Viewer GLBs remain derived runtime assets rather than facts.

## AI operating rule

Use canonical JSON for factual measurements. Use Personal Twin Memory MCP for durable AI notes and canonical reads. Use Sweet Home 3D MCP for room/furniture scene operations. Use Blender MCP for body/avatar and general 3D scene operations. Do not infer canonical body measurements from a mesh when explicit measurements exist.

The editor bridge paths are intentionally independent: Sweet Home 3D runs its plugin on container loopback `9877` and is forwarded to host `21021`; Blender MCP runs as a stdio server behind an HTTP/SSE proxy on container `9878` and host `21022`. This keeps editor-specific transports isolated from the durable memory service on `21023`.

## Body measurement loop

The body avatar can be measured, fitted and validated against private canonical body measurements
without manual Blender UI work:

    scripts/body/body-model.sh measure
    scripts/body/body-model.sh fit
    scripts/body/body-model.sh validate

See docs/body-measurement-loop.md for the MPFB hm08 landmark contract and fitting semantics.

## Seated ergonomics

A private seated workstation scene can be generated from the fitted body profile and current desk
setup without modifying the neutral avatar:

    scripts/ergonomics/seated-scene.sh build
    scripts/ergonomics/seated-scene.sh validate

See docs/seated-ergonomics-v1.md for the local coordinate system, pose contract, validation rules
and runtime outputs.
