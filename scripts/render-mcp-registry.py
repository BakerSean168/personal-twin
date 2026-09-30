#!/usr/bin/env python3
"""Render the runtime MCP registry from fixed local ports and an optional tailnet host."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def build_registry(tailnet_host: str) -> dict[str, dict[str, str]]:
    servers: dict[str, dict[str, str]] = {
        "personal-twin-memory": {
            "transport": "streamable-http",
            "localUrl": "http://127.0.0.1:21023/mcp",
        },
        "sweet-home-3d": {
            "transport": "streamable-http",
            "localUrl": "http://127.0.0.1:21021/mcp",
        },
        "blender": {
            "transport": "sse",
            "localUrl": "http://127.0.0.1:21022/sse",
        },
    }
    if tailnet_host:
        servers["personal-twin-memory"]["tailnetUrl"] = (
            f"https://{tailnet_host}:21023/mcp"
        )
        servers["sweet-home-3d"]["tailnetUrl"] = (
            f"https://{tailnet_host}:21021/mcp"
        )
        servers["blender"]["tailnetUrl"] = f"https://{tailnet_host}:21022/sse"
    return servers


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: render-mcp-registry.py OUTPUT_PATH [TAILNET_HOST]",
            file=sys.stderr,
        )
        return 2

    output = Path(sys.argv[1])
    tailnet_host = sys.argv[2].rstrip(".") if len(sys.argv) == 3 else ""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_registry(tailnet_host), indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
