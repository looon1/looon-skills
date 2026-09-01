#!/usr/bin/env python3
"""Validate the hybrid Scene Manifest used by Illustrator流程图绘制."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


SEMANTIC_TYPES = {"semantic_asset", "asset", "subject"}
DIRECT_TYPES = {
    "background", "region", "frame", "rect", "rounded_rect", "circle", "ellipse",
    "line", "polyline", "polygon", "arrow", "connector", "axis", "heatmap",
    "gradient_legend",
}


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def accepted(obj: dict[str, Any]) -> bool:
    values = [obj.get("status"), obj.get("api_status")]
    api = obj.get("api")
    if isinstance(api, dict):
        values.append(api.get("status"))
    return any(str(value).lower() in {"accepted", "completed", "pass", "passed", "success"} for value in values)


def vector_valid(obj: dict[str, Any]) -> bool:
    values = [obj.get("vector_valid"), obj.get("path_validation")]
    validation = obj.get("validation")
    if isinstance(validation, dict):
        values.extend([validation.get("vector_valid"), validation.get("path")])
    return any(value is True or str(value).lower() in {"pass", "passed", "valid"} for value in values)


def provider(obj: dict[str, Any]) -> str | None:
    value = obj.get("source")
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, dict):
        name = value.get("provider") or value.get("name")
        return str(name).lower() if name else None
    return None


def bbox_of(obj: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    if isinstance(obj.get("bbox_normalized"), dict):
        return obj["bbox_normalized"], True
    if isinstance(obj.get("normalized_bbox"), dict):
        return obj["normalized_bbox"], True
    if isinstance(obj.get("bbox"), dict):
        return obj["bbox"], obj.get("coordinate_space", "normalized") == "normalized"
    return None, False


def audit(path: Path, allow_unresolved_assets: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "FAIL", "file": str(path), "errors": [str(exc)], "warnings": []}
    if not isinstance(manifest, dict):
        return {"status": "FAIL", "file": str(path), "errors": ["Manifest must be an object."], "warnings": []}
    if manifest.get("schema_version") != "1.0":
        errors.append("Manifest schema_version must be 1.0.")

    canvas = manifest.get("canvas_size") or manifest.get("canvas")
    if not isinstance(canvas, dict) or not finite(canvas.get("width")) or not finite(canvas.get("height")):
        errors.append("Manifest requires finite canvas width and height.")
    elif canvas["width"] <= 0 or canvas["height"] <= 0:
        errors.append("Canvas width and height must be positive.")

    objects = manifest.get("objects")
    if not isinstance(objects, list) or not objects:
        errors.append("Manifest requires a non-empty objects array.")
        objects = []

    ids: set[str] = set()
    orders: set[int] = set()
    semantic_count = 0
    direct_count = 0
    manifest_root = path.resolve().parent

    for index, obj in enumerate(objects):
        if not isinstance(obj, dict):
            errors.append(f"objects[{index}] must be an object.")
            continue
        object_id = obj.get("id")
        if not isinstance(object_id, str) or not object_id:
            errors.append(f"objects[{index}] lacks a stable id.")
            object_id = f"objects[{index}]"
        elif object_id in ids:
            errors.append(f"Duplicate object id: {object_id}")
        ids.add(str(object_id))

        object_type = str(obj.get("type") or "").lower()
        if object_type not in SEMANTIC_TYPES | DIRECT_TYPES:
            errors.append(f"{object_id} has unsupported type: {object_type or '<empty>'}")
        draw_order = obj.get("draw_order", obj.get("z_index"))
        if not isinstance(draw_order, int):
            errors.append(f"{object_id} requires integer draw_order.")
        elif draw_order in orders:
            errors.append(f"Duplicate draw_order: {draw_order}")
        else:
            orders.add(draw_order)

        bbox, normalized = bbox_of(obj)
        if object_type in SEMANTIC_TYPES | {"background", "region", "frame", "rect", "rounded_rect", "circle", "ellipse", "heatmap", "gradient_legend"}:
            if bbox is None:
                errors.append(f"{object_id} requires bbox or bbox_normalized.")
            else:
                for key in ("x", "y", "width", "height"):
                    if not finite(bbox.get(key)):
                        errors.append(f"{object_id} bbox.{key} must be finite numeric.")
                if all(finite(bbox.get(key)) for key in ("x", "y", "width", "height")):
                    if bbox["width"] <= 0 or bbox["height"] <= 0:
                        errors.append(f"{object_id} bbox width/height must be positive.")
                    if normalized and (bbox["x"] < 0 or bbox["y"] < 0 or bbox["x"] + bbox["width"] > 1 or bbox["y"] + bbox["height"] > 1):
                        warnings.append(f"{object_id} normalized bbox extends beyond the canvas.")

        if object_type in SEMANTIC_TYPES:
            semantic_count += 1
            asset_svg = obj.get("asset_svg")
            if not asset_svg:
                if not allow_unresolved_assets:
                    errors.append(f"{object_id} has no asset_svg; vectorize this complex asset first.")
            else:
                asset_path = Path(str(asset_svg))
                if not asset_path.is_absolute():
                    asset_path = manifest_root / asset_path
                if not asset_path.is_file():
                    errors.append(f"{object_id} asset_svg does not exist: {asset_path}")
            if not allow_unresolved_assets:
                if provider(obj) != "supersvg":
                    errors.append(f"{object_id} complex asset must be sourced from private SuperSVG.")
                if not accepted(obj):
                    errors.append(f"{object_id} lacks an accepted model status.")
                if not vector_valid(obj):
                    errors.append(f"{object_id} lacks passing vector validation.")
        elif object_type in DIRECT_TYPES:
            direct_count += 1
            if obj.get("asset_svg") or provider(obj) == "supersvg":
                errors.append(f"{object_id} is a direct rule element and must not contain a SuperSVG asset.")

        if object_type in {"line", "connector", "axis", "arrow"}:
            has_points = isinstance(obj.get("points"), list) and len(obj["points"]) >= 2
            has_ends = all(finite(obj.get(key)) for key in ("x1", "y1", "x2", "y2"))
            if not has_points and not has_ends:
                errors.append(f"{object_id} requires points or x1/y1/x2/y2.")

    return {
        "schema_version": "1.0",
        "status": "PASS" if not errors else "FAIL",
        "file": str(path.resolve()),
        "object_count": len(objects),
        "semantic_asset_count": semantic_count,
        "direct_element_count": direct_count,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--allow-unresolved-assets", action="store_true")
    args = parser.parse_args()
    report = audit(args.manifest.resolve(strict=True), args.allow_unresolved_assets)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
