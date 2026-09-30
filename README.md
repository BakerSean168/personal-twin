# Personal Twin

Open, AI-friendly source repository for a personal digital twin.

The project keeps canonical measurements separate from editor-specific 3D files and web delivery assets.

- Canonical data: JSON validated by JSON Schema
- Space authoring: Sweet Home 3D (.sh3d)
- Body authoring: MakeHuman / MPFB + Blender
- Scene composition: Blender (.blend)
- Web delivery: glTF / GLB
- AI access: structured JSON first; editor MCP integrations for scene operations

## Principles

1. Data is the source of truth. 3D meshes are views of canonical measurements.
2. Prefer open, portable formats.
3. Keep schemas, units and provenance explicit for AI/tooling.
4. This repo is public; real personal measurements and detailed home geometry are private by default.
5. Public derivatives should be portable to a static website.

## Repository layout

- schemas/ - canonical JSON Schema contracts
- examples/ - sanitized examples committed to Git
- data/private/ - real personal measurements (gitignored)
- source/ - authoring conventions and intentionally public source assets
- exports/ - web-facing derived assets
- scripts/ - validation/export automation
- docs/ - architecture and measurement conventions

## First vertical slices

### Space

1. Measure one real room.
2. Build it in Sweet Home 3D.
3. Record canonical dimensions in a private JSON file.
4. Export a public GLB only when desired.
5. Use it for a real purchase/layout decision.

### Body

1. Measure a minimal body profile.
2. Store measurements with provenance and date.
3. Build an approximate avatar with MakeHuman/MPFB.
4. Compose/export through Blender.
5. Use structured measurements for fit decisions and the mesh for visualization.


## V1 web workbench

V1 runs the mature native editors in a browser-accessible GCP dev workbench instead of rebuilding them:

- Sweet Home 3D for room/furniture editing.
- Blender + MPFB for body/avatar generation and editing.
- Sweet Home 3D MCP and Blender MCP for AI operations.
- Tailscale Serve for private browser/MCP access.

Start with `./scripts/workbench-up.sh` and verify with `./scripts/workbench-smoke.sh`. See `docs/workbench.md` for ports, runtime layout and operating rules.

## Validate examples

    python3 -m pip install -r requirements-dev.txt
    python3 scripts/validate_json.py

## Privacy

Do not commit precise personal measurements, detailed residential geometry, private photos, scans or body scans by default. Put local records under data/private/ and private 3D sources under source/private/.

## License

Code, schemas and documentation are MIT unless a file states otherwise. Third-party assets retain their original licenses.
