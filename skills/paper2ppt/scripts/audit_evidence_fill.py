#!/usr/bin/env python3
"""Audit whether a scientific raster will underfill its planned evidence frame."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops


def content_bbox(image: Image.Image, tolerance: int) -> tuple[int, int, int, int]:
    rgb = image.convert("RGB")
    corners = [
        rgb.getpixel((0, 0)),
        rgb.getpixel((rgb.width - 1, 0)),
        rgb.getpixel((0, rgb.height - 1)),
        rgb.getpixel((rgb.width - 1, rgb.height - 1)),
    ]
    background = tuple(sorted(channel)[len(channel) // 2] for channel in zip(*corners))
    bg = Image.new("RGB", rgb.size, background)
    diff = ImageChops.difference(rgb, bg).convert("L")
    mask = diff.point(lambda value: 255 if value > tolerance else 0)
    return mask.getbbox() or (0, 0, rgb.width, rgb.height)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Accepted panel or Figure asset")
    parser.add_argument("--frame-width", required=True, type=float)
    parser.add_argument("--frame-height", required=True, type=float)
    parser.add_argument("--min-frame-fill", type=float, default=0.45)
    parser.add_argument("--min-content-fill", type=float, default=0.35)
    parser.add_argument("--background-tolerance", type=int, default=18)
    args = parser.parse_args()

    image_path = Path(args.image).expanduser().resolve()
    with Image.open(image_path) as source:
        width, height = source.size
        bbox = content_bbox(source, args.background_tolerance)

    frame_width = args.frame_width
    frame_height = args.frame_height
    scale = min(frame_width / width, frame_height / height)
    rendered_width = width * scale
    rendered_height = height * scale
    frame_area = frame_width * frame_height
    frame_fill = rendered_width * rendered_height / frame_area

    content_width = bbox[2] - bbox[0]
    content_height = bbox[3] - bbox[1]
    content_fill = (content_width * scale) * (content_height * scale) / frame_area
    aspect = width / height

    reroute = frame_fill < args.min_frame_fill or content_fill < args.min_content_fill
    if not reroute:
        route = "keep_planned_layout"
    elif aspect < 0.65:
        route = "narrow_panel_zoom_strip_or_locator_plus_zooms"
    elif aspect > 2.8:
        route = "wide_panel_zoom_stack_or_locator_plus_zooms"
    else:
        route = "reacquire_tighter_asset_or_pair_with_linked_evidence"

    report = {
        "image": str(image_path),
        "source_size": [width, height],
        "source_aspect": round(aspect, 4),
        "content_bbox": list(bbox),
        "planned_frame": [frame_width, frame_height],
        "projected_asset_fill_ratio": round(frame_fill, 4),
        "projected_content_fill_ratio": round(content_fill, 4),
        "thresholds": {
            "min_frame_fill": args.min_frame_fill,
            "min_content_fill": args.min_content_fill,
        },
        "status": "reroute" if reroute else "pass",
        "recommended_route": route,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(2 if reroute else 0)


if __name__ == "__main__":
    main()
