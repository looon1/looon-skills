#!/usr/bin/env python3
"""Validate a panel manifest and materialize crops, overlay, and contact sheet.

This script does not detect panels. It only renders explicit, auditable boxes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ALLOWED_KINDS = {"labeled_panel", "semantic_group", "shared_asset", "inset"}
ALLOWED_STATUS = {"accepted", "needs_review", "rejected"}
COLORS = {
    "accepted": (28, 137, 82, 255),
    "needs_review": (230, 143, 0, 255),
    "rejected": (201, 48, 44, 255),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_source(manifest_path: Path, source_value: str) -> Path:
    source = Path(source_value).expanduser()
    if not source.is_absolute():
        source = (manifest_path.parent / source).resolve()
    return source


def to_pixels(bbox, space: str, width: int, height: int):
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("bbox must be [left, top, right, bottom]")
    values = [float(v) for v in bbox]
    if space == "normalized":
        if any(v < 0 or v > 1 for v in values):
            raise ValueError("normalized bbox values must be in [0, 1]")
        values = [values[0] * width, values[1] * height, values[2] * width, values[3] * height]
    elif space != "pixels":
        raise ValueError("bbox_space must be pixels or normalized")
    left, top, right, bottom = [int(round(v)) for v in values]
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"bbox outside source: {[left, top, right, bottom]} vs {width}x{height}")
    return left, top, right, bottom


def load_font(size: int):
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def validate_panel(panel: dict, seen: set[str]):
    panel_id = panel.get("id")
    if not isinstance(panel_id, str) or not panel_id.strip():
        raise ValueError("every panel requires a nonempty id")
    if panel_id in seen:
        raise ValueError(f"duplicate panel id: {panel_id}")
    seen.add(panel_id)
    if panel.get("kind") not in ALLOWED_KINDS:
        raise ValueError(f"{panel_id}: invalid kind")
    if panel.get("status") not in ALLOWED_STATUS:
        raise ValueError(f"{panel_id}: invalid status")
    if not isinstance(panel.get("evidence"), list) or not panel["evidence"]:
        raise ValueError(f"{panel_id}: evidence must be a nonempty list")
    if not isinstance(panel.get("detectors"), list) or not panel["detectors"]:
        raise ValueError(f"{panel_id}: detectors must be a nonempty list")
    if panel.get("status") == "accepted":
        if not str(panel.get("reviewer_note", "")).strip():
            raise ValueError(f"{panel_id}: accepted panel requires reviewer_note")
        if not str(panel.get("caption_segment", "")).strip():
            raise ValueError(f"{panel_id}: accepted panel requires caption_segment")


def make_contact_sheet(items, destination: Path):
    if not items:
        return
    thumb_w, thumb_h = 520, 320
    columns = 2 if len(items) > 1 else 1
    rows = math.ceil(len(items) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + 54)), "white")
    draw = ImageDraw.Draw(sheet)
    font = load_font(22)
    for index, (panel_id, status, crop) in enumerate(items):
        col, row = index % columns, index // columns
        x, y = col * thumb_w, row * (thumb_h + 54)
        preview = crop.copy()
        preview.thumbnail((thumb_w - 24, thumb_h - 24), Image.Resampling.LANCZOS)
        px = x + (thumb_w - preview.width) // 2
        py = y + (thumb_h - preview.height) // 2
        sheet.paste(preview.convert("RGB"), (px, py))
        draw.text((x + 12, y + thumb_h + 10), f"{panel_id} | {status}", fill=COLORS[status][:3], font=font)
    sheet.save(destination, quality=95)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    manifest_path = Path(args.manifest).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    panels_dir = output_dir / "panels"
    output_dir.mkdir(parents=True, exist_ok=True)
    panels_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0":
        raise ValueError("schema_version must be 1.0")
    source_path = resolve_source(manifest_path, data["source_image"])
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    actual_hash = sha256(source_path)
    declared_hash = data.get("source_sha256")
    if declared_hash and declared_hash != actual_hash:
        raise ValueError("source_sha256 does not match source_image")

    source = Image.open(source_path).convert("RGBA")
    width, height = source.size
    overlay = source.copy()
    draw = ImageDraw.Draw(overlay, "RGBA")
    font = load_font(max(18, round(min(width, height) * 0.018)))
    seen = set()
    crops = []
    report_panels = []
    space = data.get("bbox_space", "pixels")

    for panel in data.get("panels", []):
        validate_panel(panel, seen)
        box = to_pixels(panel.get("bbox"), space, width, height)
        margin = int(panel.get("margin_px", 0))
        crop_box = (
            max(0, box[0] - margin),
            max(0, box[1] - margin),
            min(width, box[2] + margin),
            min(height, box[3] + margin),
        )
        color = COLORS[panel["status"]]
        draw.rectangle(box, outline=color, width=max(3, round(min(width, height) * 0.004)))
        label = f"{panel['id']} | {panel['status']}"
        label_box = draw.textbbox((box[0], box[1]), label, font=font)
        label_y = max(0, box[1] - (label_box[3] - label_box[1]) - 8)
        draw.rectangle((box[0], label_y, box[0] + label_box[2] - label_box[0] + 12, box[1]), fill=color)
        draw.text((box[0] + 6, label_y + 2), label, fill="white", font=font)

        crop = source.crop(crop_box).convert("RGB")
        filename = f"{panel['id']}.png"
        crop.save(panels_dir / filename, quality=100)
        if panel["status"] != "rejected":
            crops.append((panel["id"], panel["status"], crop))
        report_panels.append({
            "id": panel["id"],
            "status": panel["status"],
            "bbox_pixels": list(box),
            "crop_bbox_pixels": list(crop_box),
            "size": [crop.width, crop.height],
            "file": str((panels_dir / filename).resolve()),
        })

    overlay.convert("RGB").save(output_dir / "overlay_review.png", quality=95)
    make_contact_sheet(crops, output_dir / "contact_sheet.png")
    report = {
        "schema_version": "1.0",
        "figure_id": data.get("figure_id"),
        "source_image": str(source_path),
        "source_sha256": actual_hash,
        "source_size": [width, height],
        "panels": report_panels,
        "claim": "materialized_explicit_boxes_not_detected",
    }
    (output_dir / "materialization_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
