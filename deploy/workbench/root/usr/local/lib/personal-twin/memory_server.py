#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

DATA_ROOT = Path(os.environ.get("PERSONAL_TWIN_DATA_ROOT", "/data")).resolve()
MEMORY_ROOT = (DATA_ROOT / "memory").resolve()
CANONICAL_ROOT = (DATA_ROOT / "canonical").resolve()
SAFE_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

mcp = FastMCP(
    "personal-twin-memory",
    instructions=(
        "Durable private memory for Personal Twin. Canonical measurement JSON remains "
        "the source of truth; memory records may reference it but do not replace it."
    ),
    host="0.0.0.0",
    port=9880,
    streamable_http_path="/mcp",
    json_response=True,
)


def _safe_part(value: str, label: str) -> str:
    if not SAFE_PART.fullmatch(value):
        raise ValueError(
            f"{label} must match {SAFE_PART.pattern}; path separators and traversal are not allowed"
        )
    return value


def _record_path(namespace: str, key: str) -> Path:
    namespace = _safe_part(namespace, "namespace")
    key = _safe_part(key, "key")
    path = (MEMORY_ROOT / namespace / f"{key}.json").resolve()
    if MEMORY_ROOT not in path.parents:
        raise ValueError("record path escaped memory root")
    return path


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@mcp.tool()
def memory_put(
    namespace: str,
    key: str,
    value: Any,
    kind: str = "note",
    source: str | None = None,
) -> dict[str, Any]:
    """Create or replace one durable memory record using an atomic file write."""
    path = _record_path(namespace, key)
    now = datetime.now(timezone.utc).isoformat()
    created_at = now
    if path.exists():
        current = _read_json(path)
        if isinstance(current, dict):
            created_at = str(current.get("createdAt") or now)
    payload = {
        "schemaVersion": 1,
        "namespace": namespace,
        "key": key,
        "kind": kind,
        "value": value,
        "source": source,
        "createdAt": created_at,
        "updatedAt": now,
    }
    _atomic_json_write(path, payload)
    return payload


@mcp.tool()
def memory_get(namespace: str, key: str) -> dict[str, Any]:
    """Read one durable memory record."""
    path = _record_path(namespace, key)
    if not path.is_file():
        raise FileNotFoundError(f"memory record not found: {namespace}/{key}")
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("memory record is not a JSON object")
    return payload


@mcp.tool()
def memory_list(namespace: str | None = None) -> list[dict[str, Any]]:
    """List durable memory records, optionally restricted to one namespace."""
    if namespace is not None:
        namespace = _safe_part(namespace, "namespace")
        roots = [MEMORY_ROOT / namespace]
    else:
        roots = [MEMORY_ROOT]

    result: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            if not path.is_file():
                continue
            try:
                payload = _read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                result.append(
                    {
                        "namespace": payload.get("namespace"),
                        "key": payload.get("key"),
                        "kind": payload.get("kind"),
                        "source": payload.get("source"),
                        "updatedAt": payload.get("updatedAt"),
                    }
                )
    return result


@mcp.tool()
def memory_delete(namespace: str, key: str) -> dict[str, Any]:
    """Delete one durable memory record."""
    path = _record_path(namespace, key)
    existed = path.is_file()
    if existed:
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass
    return {"namespace": namespace, "key": key, "deleted": existed}


@mcp.tool()
def canonical_list() -> list[str]:
    """List canonical private JSON documents by path relative to /data/canonical."""
    if not CANONICAL_ROOT.exists():
        return []
    return [
        str(path.relative_to(CANONICAL_ROOT))
        for path in sorted(CANONICAL_ROOT.rglob("*.json"))
        if path.is_file()
    ]


@mcp.tool()
def canonical_read(document: str) -> Any:
    """Read one canonical JSON document without modifying it."""
    rel = Path(document)
    if rel.is_absolute() or ".." in rel.parts or rel.suffix != ".json":
        raise ValueError("document must be a relative .json path without traversal")
    path = (CANONICAL_ROOT / rel).resolve()
    if CANONICAL_ROOT not in path.parents:
        raise ValueError("document escaped canonical root")
    if not path.is_file():
        raise FileNotFoundError(f"canonical document not found: {document}")
    return _read_json(path)


if __name__ == "__main__":
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)
    mcp.run(transport="streamable-http")
