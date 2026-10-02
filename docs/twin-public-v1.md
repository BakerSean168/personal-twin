# twin-public-v1

`twin-public-v1` is the explicit-publication boundary for Personal Twin.

The repository itself is public, but real body measurements and detailed residential geometry are private by default. The exporter therefore does not scan the repository looking for data. It reads **only** paths listed in `exports/public/catalog.json`, and every listed record must live under `exports/public/`.

The default catalog is intentionally empty. There is currently no active first-party runtime consumer of this projection. The contract stays continuously validated on pushes and pull requests, while artifact publication is manual (`workflow_dispatch`) until a real public record/consumer requires transport. This avoids creating empty 90-day CI artifacts for unrelated private modeling changes.

Publishing a real twin fact is a deliberate two-step action:

1. create a public derivative under `exports/public/`;
2. add its relative path to `exports/public/catalog.json`.

Record types are validated against the canonical body/space/furniture JSON Schemas before publication. Binary/3D assets are hashed and represented by metadata in the v1 JSON artifact; transport of the actual binary remains an independent release/object-storage concern.

The exporter never reads:

- `data/private/`;
- `source/private/`;
- `exports/private/`.

## Commands

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/export_twin_public.py
python3 scripts/verify_twin_public.py
python3 -m unittest -v scripts/test_export_twin_public.py
```
