# Personal Twin Web Workbench

V1 deliberately reuses mature native editors instead of implementing a custom 3D editor.

## Components

- Sweet Home 3D 7.5: room, wall, opening and furniture editing.
- Sweet Home 3D MCP 1.1.0: AI access to the active home.
- Blender 5.1.2: general 3D workbench.
- MPFB 2.0.17: parametric human generation/editing inside Blender.
- Blender MCP 1.0.0: AI inspection and scene editing.
- LinuxServer Webtop: browser delivery of the native desktop applications.
- Tailscale Serve: private HTTPS ingress for the workbench and MCP endpoints.

## Runtime

The runtime is intentionally ignored by Git:

- `runtime/data/canonical/`: canonical private JSON.
- `runtime/data/spaces/`: Sweet Home 3D source files.
- `runtime/data/body/`: Blender/MPFB body source files.
- `runtime/data/exports/`: derived web/export assets.
- `runtime/data/mcp/servers.json`: actual local/tailnet MCP endpoints.
- `runtime/workbench/config/`: persistent editor preferences and installed extensions.

The public repository contains only code, schemas, documentation and sanitized examples.

## Ports on GCP dev

| Port | Service |
| --- | --- |
| 21020 | Browser workbench |
| 21021 | Sweet Home 3D MCP (Streamable HTTP `/mcp`) |
| 21022 | Blender MCP (SSE `/sse`) |

All host ports bind to loopback. Remote access is provided through Tailscale Serve only.

## Start

Run `./scripts/workbench-up.sh`.

The start script prints the node-specific Tailscale HTTPS URL. The public repository intentionally does not hardcode the private tailnet hostname.

The desktop auto-starts Sweet Home 3D and Blender + MPFB. Desktop shortcuts are also available if either application is closed.

## Verify

Run `./scripts/workbench-smoke.sh`.

The smoke test verifies Webtop, Sweet Home 3D MCP, Blender MCP, and required source assets.

## Current V1 seed

The local runtime seeds the first private room from canonical JSON. Exact residential dimensions remain in ignored runtime/private data and are not committed to this public repository. The Sweet Home 3D source is `runtime/data/spaces/bedroom/bedroom.sh3d`.

The first body asset is a generic MPFB base human at `runtime/data/body/avatar.blend`. It is intentionally not populated with real personal measurements yet.

## AI operating rule

Use canonical JSON for factual measurements. Use Sweet Home 3D MCP for room/furniture scene operations. Use Blender MCP for body/avatar and general 3D scene operations. Do not infer canonical body measurements from a mesh when explicit measurements exist.
