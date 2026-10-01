#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "generated/twin-public-v1.json")
data = json.loads(path.read_text(encoding="utf-8"))
if data.get("schemaVersion") != 1 or data.get("product") != "twin-public-v1":
    raise SystemExit("invalid twin-public-v1 envelope")
if data.get("generated") is not True or data.get("editable") is not False:
    raise SystemExit("invalid mutability markers")
if not re.fullmatch(r"[0-9a-f]{40}", str((data.get("source") or {}).get("revision", ""))):
    raise SystemExit("source revision must be a full Git SHA")
raw = path.read_text(encoding="utf-8")
if "data/private" in raw or "source/private" in raw or "exports/private" in raw:
    raise SystemExit("private source path leaked into twin-public-v1")
print(
    "twin-public-v1=PASS "
    f"spaces={len(data['payload']['spaces'])} bodyProfiles={len(data['payload']['bodyProfiles'])} "
    f"furnitureLayouts={len(data['payload']['furnitureLayouts'])} assets={len(data['payload']['assets'])}"
)
