#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
viewer_url="${PERSONAL_TWIN_VIEWER_URL:-http://127.0.0.1:21024}"
image="${PERSONAL_TWIN_WORKBENCH_IMAGE:-personal-twin-workbench:local}"

declare -A expected_title=(
  [room]="Bedroom"
  [combined]="Integrated Room + Body"
  [standing]="Standing Body"
  [seated]="Seated Workstation"
)

declare -A expected_metric=(
  [room]="房间外包络"
  [combined]="显示器距离"
  [standing]="几何高度差"
  [seated]="视距"
)

curl -fsS --max-time 5 "$viewer_url/healthz" >/dev/null

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for mode in room combined standing seated; do
  dom="$tmp_dir/$mode.html"
  log="$tmp_dir/$mode.log"

  docker run --rm --network host     --entrypoint /bin/sh     "$image"     -lc "xvfb-run -a chromium       --headless=new       --no-sandbox       --disable-dev-shm-usage       --enable-webgl       --enable-unsafe-swiftshader       --virtual-time-budget=10000       --dump-dom '$viewer_url/?mode=$mode&renderProbe=1'"     >"$dom" 2>"$log"

  grep -Fq '<canvas data-engine="three.js' "$dom"
  grep -Fq "id=\"mode-title\">${expected_title[$mode]}<" "$dom"
  grep -Fq "${expected_metric[$mode]}" "$dom"
  grep -Fq 'data-render-probe="ok"' "$dom"

  if grep -Eq 'id="loading" class="[^"]*is-visible' "$dom"; then
    printf 'Viewer mode %s never left loading state\n' "$mode" >&2
    tail -80 "$log" >&2 || true
    exit 1
  fi

  printf 'OK Twin Viewer browser mode: %s\n' "$mode"
done
