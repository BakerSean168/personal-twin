# Architecture

## Purpose

Personal Twin owns canonical personal spatial/body measurements and the conventions required to derive interoperable 3D assets. It deliberately does not start as a web application.

## Ownership boundaries

| Layer | Owner / format | Role |
| --- | --- | --- |
| Canonical facts | JSON + JSON Schema | Measurements, dimensions, provenance |
| Space authoring | Sweet Home 3D | Human-friendly room editing |
| Body authoring | MakeHuman / MPFB | Parametric avatar editing |
| Composition | Blender | Combine space, body and imported assets |
| AI scene operations | MCP adapters | Inspect and edit editor scenes |
| Web delivery | glTF / GLB | Portable rendering asset |
| Website | Digital Biome or another consumer | Presentation only |

## Data flow

Manual measurements/scans -> canonical JSON -> authoring tools -> Blender -> GLB/glTF -> Digital Biome/web.

AI should read canonical JSON for measurements and use editor MCP integrations for spatial/scene operations.

## Public/private boundary

The GitHub repository is public. The default commit boundary contains contracts, examples, docs, scripts and explicitly public derivatives. Real measurements and detailed residential geometry require an explicit publication step before entering Git history.

## V1 non-goals

- No custom room editor.
- No custom avatar editor.
- No authentication or database.
- No exact-anatomy reconstruction from sparse measurements.
- No clothing simulation engine.
- No replacement for Blender, Sweet Home 3D, MakeHuman or MPFB.
