#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
room_dir="$repo_root/runtime/data/spaces/bedroom"
source_file="$room_dir/bedroom.sh3d"
target_file="$room_dir/bedroom.sh3x"
next_file="$room_dir/bedroom.sh3x.next"

if [[ ! -f "$source_file" ]]; then
  echo "missing source room: $source_file" >&2
  exit 1
fi

if [[ -f "$target_file" && ! "$source_file" -nt "$target_file" ]]; then
  echo "web room is already current"
  exit 0
fi

rm -f "$next_file"
docker compose -f "$repo_root/deploy/space-converter/compose.yaml" run --rm   converter   /data/bedroom.sh3d   /data/bedroom.sh3x.next >/dev/null
mv -f "$next_file" "$target_file"

echo "synced desktop/MCP room -> web room"
