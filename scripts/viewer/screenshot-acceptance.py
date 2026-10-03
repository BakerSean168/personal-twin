#!/usr/bin/env python3
"""Validate that a Chromium screenshot contains a usable Viewer composition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


# Broad envelopes from visually accepted 900x700 compositions. These are
# intentionally not golden-image diffs: they catch blank, tiny, or over-zoomed
# subjects while tolerating normal antialiasing/renderer differences.
COVERAGE = {
    "room": (0.20, 0.75),
    "combined": (0.35, 0.90),
    "standing": (0.025, 0.20),
    "seated": (0.12, 0.60),
}

BRIGHT_CHANNEL_MIN = 70
BRIGHT_SUM_MIN = 180


def parse_rect(value: str) -> tuple[int, int, int, int]:
    parts = [int(part) for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("rect must be x,y,width,height")
    x, y, width, height = parts
    if min(width, height) <= 0:
        raise argparse.ArgumentTypeError("rect width/height must be positive")
    return x, y, width, height


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=sorted(COVERAGE))
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--rect", required=True, type=parse_rect)
    args = parser.parse_args()

    image = Image.open(args.image).convert("RGB")
    x, y, width, height = args.rect
    right = x + width
    bottom = y + height
    if x < 0 or y < 0 or right > image.width or bottom > image.height:
        raise SystemExit(
            f"viewport rect {args.rect} is outside screenshot {image.width}x{image.height}"
        )

    viewport = image.crop((x, y, right, bottom))
    pixels = (
        viewport.get_flattened_data()
        if hasattr(viewport, "get_flattened_data")
        else viewport.getdata()
    )
    total = width * height
    bright = sum(
        1
        for red, green, blue in pixels
        if max(red, green, blue) >= BRIGHT_CHANNEL_MIN
        and red + green + blue >= BRIGHT_SUM_MIN
    )
    ratio = bright / total
    minimum, maximum = COVERAGE[args.mode]

    print(
        f"Viewer screenshot {args.mode}: bright={bright}/{total} "
        f"ratio={ratio:.4f} expected={minimum:.3f}..{maximum:.3f}"
    )
    if ratio < minimum or ratio > maximum:
        print(
            f"Screenshot acceptance failed for {args.mode}: "
            f"bright coverage {ratio:.4f} is outside {minimum:.3f}..{maximum:.3f}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
