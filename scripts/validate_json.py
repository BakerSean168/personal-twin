#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("schemas/body.schema.json", "examples/body.example.json"),
    ("schemas/space.schema.json", "examples/space.example.json"),
    ("schemas/furniture.schema.json", "examples/furniture.example.json"),
    ("schemas/ergonomics.schema.json", "examples/ergonomics.example.json"),
]


def load_json(relative_path: str) -> dict:
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    failures = 0
    for schema_path, data_path in CASES:
        schema = load_json(schema_path)
        instance = load_json(data_path)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda error: [str(part) for part in error.absolute_path],
        )
        if errors:
            failures += 1
            print(f"FAIL {data_path} against {schema_path}")
            for error in errors:
                where = ".".join(str(part) for part in error.absolute_path) or "<root>"
                print(f"  {where}: {error.message}")
        else:
            print(f"OK   {data_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
