#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import mimetypes
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = (ROOT / "exports" / "public").resolve()
CATALOG_PATH = PUBLIC_ROOT / "catalog.json"
OUTPUT_DIR = ROOT / "generated"
REPOSITORY = "https://github.com/BakerSean168/personal-twin.git"
PRODUCER = "pds://system/component/personal-twin"


class ProjectionError(ValueError):
    pass


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def safe_public_path(relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ProjectionError("public export path must be a non-empty string")
    candidate = (PUBLIC_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(PUBLIC_ROOT)
    except ValueError as exc:
        raise ProjectionError(f"public export path escapes exports/public: {relative_path}") from exc
    if candidate == CATALOG_PATH:
        raise ProjectionError("catalog.json cannot be exported as a domain record")
    if not candidate.is_file():
        raise ProjectionError(f"public export file not found: {relative_path}")
    return candidate


def validate_record(path: Path, schema_relative: str) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise ProjectionError(f"{path.relative_to(ROOT)} must contain an object")
    schema = load_json(ROOT / schema_relative)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(value), key=lambda e: [str(x) for x in e.absolute_path])
    if errors:
        detail = "; ".join(f"{'.'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors[:5])
        raise ProjectionError(f"{path.relative_to(ROOT)} failed {schema_relative}: {detail}")
    return value


def listed_records(catalog: dict[str, Any], key: str, schema: str) -> list[dict[str, Any]]:
    values = catalog.get(key, [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ProjectionError(f"catalog.{key} must be a list of paths")
    return [validate_record(safe_public_path(value), schema) for value in values]


def listed_assets(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    values = catalog.get("assets", [])
    if not isinstance(values, list):
        raise ProjectionError("catalog.assets must be a list")
    result: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise ProjectionError("catalog.assets entries must be objects")
        asset_id = item.get("id")
        kind = item.get("kind")
        relative_path = item.get("path")
        if not all(isinstance(value, str) and value for value in (asset_id, kind, relative_path)):
            raise ProjectionError("catalog.assets requires id, kind and path")
        if asset_id in ids:
            raise ProjectionError(f"duplicate public asset id: {asset_id}")
        ids.add(asset_id)
        path = safe_public_path(relative_path)
        data = path.read_bytes()
        media_type = item.get("mediaType")
        if media_type is not None and not isinstance(media_type, str):
            raise ProjectionError(f"catalog asset {asset_id} mediaType must be a string")
        result.append(
            {
                "id": asset_id,
                "kind": kind,
                "path": relative_path,
                "mediaType": media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    return result


def build_projection() -> dict[str, Any]:
    catalog = load_json(CATALOG_PATH)
    if not isinstance(catalog, dict) or catalog.get("schemaVersion") != 1:
        raise ProjectionError("exports/public/catalog.json must use schemaVersion 1")
    allowed = {"schemaVersion", "spaces", "bodyProfiles", "furnitureLayouts", "assets"}
    unexpected = sorted(set(catalog) - allowed)
    if unexpected:
        raise ProjectionError(f"unsupported catalog keys: {unexpected}")
    return {
        "schemaVersion": 1,
        "product": "twin-public-v1",
        "generated": True,
        "editable": False,
        "producer": PRODUCER,
        "source": {"repository": REPOSITORY, "revision": git("rev-parse", "HEAD")},
        "payload": {
            "spaces": listed_records(catalog, "spaces", "schemas/space.schema.json"),
            "bodyProfiles": listed_records(catalog, "bodyProfiles", "schemas/body.schema.json"),
            "furnitureLayouts": listed_records(catalog, "furnitureLayouts", "schemas/furniture.schema.json"),
            "assets": listed_assets(catalog),
        },
    }


def write_projection() -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    projection = build_projection()
    artifact = OUTPUT_DIR / "twin-public-v1.json"
    manifest = OUTPUT_DIR / "twin-public-v1.manifest.json"
    artifact.write_text(json.dumps(projection, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "apiVersion": "pds/v1alpha1",
                "kind": "DataProductManifest",
                "metadata": {"id": "twin-public-v1"},
                "spec": {
                    "producer": {"ref": PRODUCER},
                    "contract": {"name": "twin-public", "version": "v1"},
                    "source": projection["source"],
                    "artifact": {
                        "path": "generated/twin-public-v1.json",
                        "mediaType": "application/vnd.pds.twin-public-v1+json",
                        "generated": True,
                        "editable": False,
                    },
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    payload = projection["payload"]
    print(
        "twin-public-v1="
        f"spaces={len(payload['spaces'])} bodyProfiles={len(payload['bodyProfiles'])} "
        f"furnitureLayouts={len(payload['furnitureLayouts'])} assets={len(payload['assets'])}"
    )
    print(f"artifact={artifact}")
    print(f"manifest={manifest}")
    return artifact, manifest


if __name__ == "__main__":
    write_projection()
