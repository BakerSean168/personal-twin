#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
viewer_url="${PERSONAL_TWIN_VIEWER_URL:-http://127.0.0.1:21024}"
image="${PERSONAL_TWIN_WORKBENCH_IMAGE:-personal-twin-workbench:local}"
window_size="900,700"

declare -A expected_title=(
  [room]="Bedroom"
  [combined]="Integrated Room + Body"
  [standing]="Standing Body"
)

declare -A expected_metric=(
  [room]="房间外包络"
  [combined]="显示器距离"
  [standing]="几何高度差"
)

curl -fsS --max-time 5 "$viewer_url/healthz" >/dev/null

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for mode in room combined standing; do
  dom="$tmp_dir/$mode.html"
  log="$tmp_dir/$mode.log"
  screenshot="$tmp_dir/$mode.png"
  screenshot_log="$tmp_dir/$mode-screenshot.log"
  url="$viewer_url/?mode=$mode&renderProbe=1"

  docker run --rm --network host --entrypoint /bin/sh "$image" -lc "xvfb-run -a chromium --headless=new --no-sandbox --disable-dev-shm-usage --enable-webgl --enable-unsafe-swiftshader --hide-scrollbars --window-size=$window_size --virtual-time-budget=10000 --dump-dom '$url'" >"$dom" 2>"$log"

  grep -Fq '<canvas data-engine="three.js' "$dom"
  grep -Fq "id=\"mode-title\">${expected_title[$mode]}<" "$dom"
  grep -Fq "${expected_metric[$mode]}" "$dom"
  if [[ "$mode" == "combined" ]]; then
    grep -Fq "参考检查" "$dom"
    grep -Fq "屏幕离桌面" "$dom"
    grep -Fq "215–575 mm" "$dom"
    grep -Fq "模型头顶/屏顶" "$dom"
    grep -Fq "+75 mm · 坐高待复核" "$dom"
    grep -Fq "显示器高度" "$dom"
    grep -Fq "模型建议下移 ≈72 mm · 暂缓" "$dom"
    grep -Fq "鼠标布局" "$dom"
  fi
  grep -Fq 'data-render-probe="ok"' "$dom"

  if grep -Eq 'id="loading" class="[^"]*is-visible' "$dom"; then
    printf 'Viewer mode %s never left loading state\n' "$mode" >&2
    tail -80 "$log" >&2 || true
    exit 1
  fi

  render_rect="$(grep -o 'data-render-rect="[^"]*"' "$dom" | head -1 | cut -d'"' -f2)"
  if [[ -z "$render_rect" ]]; then
    printf 'Viewer mode %s did not publish its viewport rectangle\n' "$mode" >&2
    exit 1
  fi

  docker run --rm --network host -v "$tmp_dir:/out" --entrypoint /bin/sh "$image" -lc "xvfb-run -a chromium --headless=new --no-sandbox --disable-dev-shm-usage --enable-webgl --enable-unsafe-swiftshader --hide-scrollbars --window-size=$window_size --virtual-time-budget=10000 --screenshot=/out/$mode.png '$url'" >"$screenshot_log" 2>&1
  test -s "$screenshot"

  docker run --rm -v "$repo_root:/repo:ro" -v "$tmp_dir:/out:ro" --entrypoint /lsiopy/bin/python3 "$image" /repo/scripts/viewer/screenshot-acceptance.py --mode "$mode" --image "/out/$mode.png" --rect "$render_rect"

  printf 'OK Twin Viewer browser mode: %s\n' "$mode"
done

# Backward compatibility: the retired seated route resolves to the integrated
# room + body view rather than falling back to an unrelated mode.
legacy_dom="$tmp_dir/legacy-seated.html"
docker run --rm --network host --entrypoint /bin/sh "$image" -lc "xvfb-run -a chromium --headless=new --no-sandbox --disable-dev-shm-usage --enable-webgl --enable-unsafe-swiftshader --hide-scrollbars --window-size=$window_size --virtual-time-budget=10000 --dump-dom '$viewer_url/?mode=seated'" >"$legacy_dom" 2>/dev/null
grep -Fq 'id="mode-title">Integrated Room + Body<' "$legacy_dom"
grep -Fq '参考检查' "$legacy_dom"
printf 'OK Twin Viewer legacy seated route -> combined\n'
