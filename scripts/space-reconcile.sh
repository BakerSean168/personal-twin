#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
room_dir="$repo_root/runtime/data/spaces/bedroom"
desktop_file="$room_dir/bedroom.sh3d"
web_file="$room_dir/bedroom.sh3x"
converter_compose="$repo_root/deploy/space-converter/compose.yaml"

convert() {
  local source_name="$1"
  local target_name="$2"
  local target_path="$room_dir/$target_name"
  local next_name="$target_name.next"

  rm -f "$room_dir/$next_name"
  docker compose -f "$converter_compose" run --rm     converter     "/data/$source_name"     "/data/$next_name" >/dev/null
  mv -f "$room_dir/$next_name" "$target_path"
}

if [[ -f "$web_file" && -f "$desktop_file" ]]; then
  if [[ "$web_file" -nt "$desktop_file" ]]; then
    convert bedroom.sh3x bedroom.sh3d
    echo "reconciled newer web room -> desktop/MCP room"
  elif [[ "$desktop_file" -nt "$web_file" ]]; then
    convert bedroom.sh3d bedroom.sh3x
    echo "reconciled newer desktop/MCP room -> web room"
  else
    echo "room formats already reconciled"
  fi
elif [[ -f "$web_file" ]]; then
  convert bedroom.sh3x bedroom.sh3d
  echo "created desktop/MCP room from web room"
elif [[ -f "$desktop_file" ]]; then
  convert bedroom.sh3d bedroom.sh3x
  echo "created web room from desktop/MCP room"
else
  echo "no room source exists yet; skipping format reconciliation"
fi
