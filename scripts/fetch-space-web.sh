#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="7.5.2"
sha256="f48c45d6e9c94543ea1f01a003d72667846bd8bde7eb41fe58f675c806009931"
vendor_dir="$repo_root/deploy/space-web/vendor"
target="$vendor_dir/SweetHome3DJS-$version.zip"

mkdir -p "$vendor_dir"

valid_archive() {
  [[ -f "$1" ]] || return 1
  local actual
  actual="$(sha256sum "$1" | awk '{print $1}')"
  [[ "$actual" == "$sha256" ]]
}

if valid_archive "$target"; then
  echo "SweetHome3DJS $version archive cache is ready"
  exit 0
fi

candidates=()
if [[ -n "${SWEETHOME3DJS_ARCHIVE:-}" ]]; then
  candidates+=("$SWEETHOME3DJS_ARCHIVE")
fi
candidates+=(
  "/tmp/SweetHome3DJS-$version.zip"
  "$HOME/.cache/personal-twin/SweetHome3DJS-$version.zip"
)

for candidate in "${candidates[@]}"; do
  if valid_archive "$candidate"; then
    cp "$candidate" "$target"
    echo "Seeded SweetHome3DJS archive cache from $candidate"
    exit 0
  fi
done

tmp="$target.download"
rm -f "$tmp"

urls=(
  "https://phoenixnap.dl.sourceforge.net/project/sweethome3d/SweetHome3DJS/SweetHome3DJS-$version.zip"
  "https://netix.dl.sourceforge.net/project/sweethome3d/SweetHome3DJS/SweetHome3DJS-$version.zip"
  "https://pilotfiber.dl.sourceforge.net/project/sweethome3d/SweetHome3DJS/SweetHome3DJS-$version.zip"
  "https://sourceforge.net/projects/sweethome3d/files/SweetHome3DJS/SweetHome3DJS-$version.zip/download"
)

for url in "${urls[@]}"; do
  echo "Fetching SweetHome3DJS $version from $url"
  rm -f "$tmp"
  if curl -fL --retry 2 --connect-timeout 10 --max-time 180 "$url" -o "$tmp"; then
    if valid_archive "$tmp"; then
      mv "$tmp" "$target"
      echo "Cached SweetHome3DJS $version"
      exit 0
    fi
    echo "Checksum mismatch from $url" >&2
  fi
done

rm -f "$tmp"
echo "Unable to fetch a verified SweetHome3DJS $version archive" >&2
exit 1
