#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
schema_path = ROOT / "schemas" / "ergonomics.schema.json"
instance_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "runtime" / "data" / "canonical" / "ergonomics" / "desk-setup.json"

schema = json.loads(schema_path.read_text(encoding="utf-8"))
instance = json.loads(instance_path.read_text(encoding="utf-8"))
validator = Draft202012Validator(schema, format_checker=FormatChecker())
errors = sorted(validator.iter_errors(instance), key=lambda error: [str(part) for part in error.absolute_path])
if errors:
    for error in errors:
        where = ".".join(str(part) for part in error.absolute_path) or "<root>"
        print(f"{where}: {error.message}", file=sys.stderr)
    raise SystemExit(1)

print(f"OK {instance_path}")
