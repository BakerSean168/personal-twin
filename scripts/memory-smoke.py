#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request

BASE = os.environ.get("PERSONAL_TWIN_MEMORY_MCP_URL", "http://127.0.0.1:21023/mcp")


def post(payload: dict, session_id: str | None = None):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    request = urllib.request.Request(
        BASE,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        raw = response.read()
        return response.headers, json.loads(raw) if raw else None


def call_tool(session_id: str, request_id: int, name: str, arguments: dict):
    _, response = post(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        session_id,
    )
    if "error" in response:
        raise RuntimeError(response["error"])
    return response["result"]


def structured(result: dict):
    if result.get("structuredContent"):
        return result["structuredContent"].get("result", result["structuredContent"])
    text = result["content"][0]["text"]
    return json.loads(text)


def main() -> None:
    headers, _ = post(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "personal-twin-memory-smoke", "version": "1.0"},
            },
        }
    )
    session_id = headers.get("Mcp-Session-Id")
    if not session_id:
        raise RuntimeError("memory MCP did not return Mcp-Session-Id")
    post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, session_id)

    documents = structured(call_tool(session_id, 2, "canonical_list", {}))
    assert "spaces/bedroom/room.json" in documents
    assert "body/profile.json" in documents

    room = structured(
        call_tool(
            session_id,
            3,
            "canonical_read",
            {"document": "spaces/bedroom/room.json"},
        )
    )
    assert room["spaceId"]

    record = structured(
        call_tool(
            session_id,
            4,
            "memory_put",
            {
                "namespace": "smoke",
                "key": "roundtrip",
                "value": {"status": "ok", "spaceId": room["spaceId"]},
                "kind": "test",
                "source": "workbench-smoke",
            },
        )
    )
    assert record["value"]["status"] == "ok"

    fetched = structured(
        call_tool(session_id, 5, "memory_get", {"namespace": "smoke", "key": "roundtrip"})
    )
    assert fetched["value"]["spaceId"] == room["spaceId"]

    records = structured(call_tool(session_id, 6, "memory_list", {"namespace": "smoke"}))
    assert any(item["key"] == "roundtrip" for item in records)

    deleted = structured(
        call_tool(session_id, 7, "memory_delete", {"namespace": "smoke", "key": "roundtrip"})
    )
    assert deleted["deleted"] is True
    print("OK Personal Twin Memory MCP: canonical read + CRUD roundtrip")


if __name__ == "__main__":
    main()
