#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
docker compose -f "$repo_root/deploy/twin-viewer/compose.yaml" down
docker compose -f "$repo_root/deploy/space-web/compose.yaml" down
docker compose -f "$repo_root/deploy/workbench/compose.yaml" down
