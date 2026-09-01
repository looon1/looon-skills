#!/usr/bin/env python3
"""Compose direct SVG primitives and model-generated complex assets."""

from __future__ import annotations

import argparse
import copy
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

SEMANTIC_TYPES = {"semantic_asset", "asset", "subject"}
STYLE_KEYS = {
    "fill", "stroke", "stroke_width", "stroke_linecap", "stroke_linejoin",
    "stroke_dasharray", "fill_opacity", "stroke_opacity", "opacity",
}


def q(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def number(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def canvas_of(manifest: dict[str, Any]) -> tuple[float, float]:
    canvas = manifest.get("canvas_size") or manifest.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("scene manifest requires canvas_size or canvas")
    width = number(canvas.get("width"), "canvas.width")
    height = number(canvas.get("height"), "canvas.height")
    if width <= 0 or height <= 0:
        raise ValueError("canvas width/height must be positive")
    return width, height


def normalized(obj: dict[str, Any]) -> bool:
    return obj.get("coordinate_space", "normalized") == "normalized"


def xy(value: Any, extent: float, is_normalized: bool, name: str) -> float:
    result = number(value, name)
    return result * extent if is_normalized else result


def bbox_of(obj: dict[str, Any], width: float, height: float) -> tuple[float, float, float, float]:
    bbox = obj.get("bbox_normalized") or obj.get("normalized_bbox") or obj.get("bbox")
    if not isinstance(bbox, dict):
        raise ValueError(f"{obj.get('id')} requires bbox")
    is_normalized = "bbox_normalized" in obj or "normalized_bbox" in obj or normalized(obj)
    x = xy(bbox.get("x"), width, is_normalized, "bbox.x")
    y = xy(bbox.get("y"), height, is_normalized, "bbox.y")
    w = xy(bbox.get("width"), width, is_normalized, "bbox.width")
    h = xy(bbox.get("height"), height, is_normalized, "bbox.height")
    if w <= 0 or h <= 0:
        raise ValueError(f"{obj.get('id')} bbox width/height must be positive")
    return x, y, w, h


def points_of(obj: dict[str, Any], width: float, height: float) -> list[tuple[float, float]]:
    is_normalized = normalized(obj)
    raw = obj.get("points")
    if isinstance(raw, list) and len(raw) >= 2:
        result: list[tuple[float, float]] = []
        for index, item in enumerate(raw):
            if isinstance(item, dict):
                px, py = item.get("x"), item.get("y")
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                px, py = item
            else:
                raise ValueError(f"{obj.get('id')} points[{index}] is invalid")
            result.append((xy(px, width, is_normalized, "point.x"), xy(py, height, is_normalized, "point.y")))
        return result
    return [
        (xy(obj.get("x1"), width, is_normalized, "x1"), xy(obj.get("y1"), height, is_normalized, "y1")),
        (xy(obj.get("x2"), width, is_normalized, "x2"), xy(obj.get("y2"), height, is_normalized, "y2")),
    ]


def style_of(obj: dict[str, Any], defaults: dict[str, str]) -> dict[str, str]:
    values: dict[str, Any] = dict(defaults)
    if isinstance(obj.get("style"), dict):
        values.update(obj["style"])
    for key in STYLE_KEYS:
        if key in obj:
            values[key] = obj[key]
    return {key.replace("_", "-"): str(value) for key, value in values.items() if value is not None}


def apply_gradient(defs: ET.Element, obj: dict[str, Any], attrs: dict[str, str]) -> None:
    gradient = obj.get("gradient")
    if not isinstance(gradient, dict):
        return
    gradient_id = f"gradient-{obj['id']}"
    kind = str(gradient.get("type", "linear")).lower()
    if kind == "radial":
        element = ET.SubElement(defs, q("radialGradient"), {
            "id": gradient_id,
            "cx": str(gradient.get("cx", "50%")),
            "cy": str(gradient.get("cy", "50%")),
            "r": str(gradient.get("r", "50%")),
        })
    else:
        element = ET.SubElement(defs, q("linearGradient"), {
            "id": gradient_id,
            "x1": str(gradient.get("x1", "0%")),
            "y1": str(gradient.get("y1", "0%")),
            "x2": str(gradient.get("x2", "100%")),
            "y2": str(gradient.get("y2", "100%")),
        })
    stops = gradient.get("stops")
    if not isinstance(stops, list) or len(stops) < 2:
        raise ValueError(f"{obj['id']} gradient requires at least two stops")
    for stop in stops:
        if not isinstance(stop, dict) or "offset" not in stop or "color" not in stop:
            raise ValueError(f"{obj['id']} has an invalid gradient stop")
        stop_attrs = {"offset": str(stop["offset"]), "stop-color": str(stop["color"])}
        if "opacity" in stop:
            stop_attrs["stop-opacity"] = str(stop["opacity"])
        ET.SubElement(element, q("stop"), stop_attrs)
    attrs["fill"] = f"url(#{gradient_id})"


def base_attrs(obj: dict[str, Any], source: str) -> dict[str, str]:
    return {
        "id": str(obj["id"]),
        "data-illustrator-flowchart-source": source,
        "data-draw-order": str(obj.get("draw_order", obj.get("z_index", 0))),
    }


def parse_asset_viewbox(root: ET.Element) -> tuple[float, float, float, float]:
    raw = root.get("viewBox")
    if raw:
        parts = [float(part) for part in re.split(r"[\s,]+", raw.strip()) if part]
        if len(parts) == 4 and parts[2] > 0 and parts[3] > 0:
            return parts[0], parts[1], parts[2], parts[3]
    def dimension(name: str) -> float:
        return float(re.sub(r"[^0-9.+-]", "", root.get(name, "0")) or 0)
    width, height = dimension("width"), dimension("height")
    if width <= 0 or height <= 0:
        raise ValueError("asset SVG requires viewBox or numeric width/height")
    return 0.0, 0.0, width, height


def prefix_asset_ids(nodes: list[ET.Element], prefix: str) -> None:
    mapping: dict[str, str] = {}
    for node in nodes:
        for element in node.iter():
            old_id = element.get("id")
            if old_id:
                mapping[old_id] = f"{prefix}-{old_id}"
    for node in nodes:
        for element in node.iter():
            old_id = element.get("id")
            if old_id in mapping:
                element.set("id", mapping[old_id])
            for key, value in list(element.attrib.items()):
                updated = value
                for source, target in mapping.items():
                    updated = updated.replace(f"url(#{source})", f"url(#{target})")
                    if updated == f"#{source}":
                        updated = f"#{target}"
                if updated != value:
                    element.set(key, updated)


def add_semantic_asset(root: ET.Element, defs: ET.Element, obj: dict[str, Any], manifest_root: Path, width: float, height: float) -> None:
    asset_path = Path(str(obj.get("asset_svg") or ""))
    if not asset_path.is_absolute():
        asset_path = manifest_root / asset_path
    tree = ET.parse(asset_path.resolve(strict=True))
    asset_root = tree.getroot()
    if asset_root.tag.split("}")[-1] != "svg":
        raise ValueError(f"{obj['id']} asset root is not svg")
    forbidden = {"image", "script", "foreignObject"}
    found = sorted({node.tag.split("}")[-1] for node in asset_root.iter()} & forbidden)
    if found:
        raise ValueError(f"{obj['id']} asset contains forbidden nodes: {', '.join(found)}")
    x, y, w, h = bbox_of(obj, width, height)
    vx, vy, vw, vh = parse_asset_viewbox(asset_root)
    preserve = str(obj.get("preserve_aspect_ratio", "meet")).lower()
    if preserve == "stretch":
        sx, sy = w / vw, h / vh
        tx, ty = x - vx * sx, y - vy * sy
    else:
        scale = min(w / vw, h / vh)
        sx = sy = scale
        tx = x + (w - vw * scale) / 2 - vx * scale
        ty = y + (h - vh * scale) / 2 - vy * scale
    group_attrs = base_attrs(obj, "supersvg-complex-asset")
    if obj.get("clip_to_bbox", True):
        clip_id = f"clip-{obj['id']}"
        clip = ET.SubElement(defs, q("clipPath"), {"id": clip_id, "clipPathUnits": "userSpaceOnUse"})
        contours = obj.get("clip_contours")
        if isinstance(contours, list) and contours:
            commands: list[str] = []
            for contour in contours:
                if not isinstance(contour, list) or len(contour) < 3:
                    continue
                converted = []
                for point in contour:
                    if not isinstance(point, (list, tuple)) or len(point) != 2:
                        raise ValueError(f"{obj['id']} has an invalid clip contour point")
                    converted.append((x + number(point[0], "clip.x") * w, y + number(point[1], "clip.y") * h))
                commands.append("M " + " L ".join(f"{fmt(px)} {fmt(py)}" for px, py in converted) + " Z")
            if not commands:
                raise ValueError(f"{obj['id']} has no usable clip contours")
            ET.SubElement(clip, q("path"), {
                "id": f"{clip_id}-path",
                "d": " ".join(commands),
                "fill-rule": "evenodd",
                "clip-rule": "evenodd",
            })
        else:
            ET.SubElement(clip, q("rect"), {"id": f"{clip_id}-rect", "x": fmt(x), "y": fmt(y), "width": fmt(w), "height": fmt(h)})
        group_attrs["clip-path"] = f"url(#{clip_id})"
    group = ET.SubElement(root, q("g"), group_attrs)
    transformed = ET.SubElement(group, q("g"), {
        "transform": f"translate({fmt(tx)} {fmt(ty)}) scale({fmt(sx)} {fmt(sy)})"
    })
    definition_copies: list[ET.Element] = []
    content_copies: list[ET.Element] = []
    for child in list(asset_root):
        if child.tag.split("}")[-1] == "defs":
            for definition in list(child):
                definition_copies.append(copy.deepcopy(definition))
        else:
            content_copies.append(copy.deepcopy(child))
    prefix_asset_ids(definition_copies + content_copies, str(obj["id"]))
    for definition in definition_copies:
        defs.append(definition)
    for content in content_copies:
        transformed.append(content)


def add_arrow(root: ET.Element, obj: dict[str, Any], width: float, height: float) -> None:
    points = points_of(obj, width, height)
    group = ET.SubElement(root, q("g"), base_attrs(obj, "direct-rule"))
    style = style_of(obj, {"fill": "none", "stroke": "#536274", "stroke_width": "3", "stroke_linecap": "round", "stroke_linejoin": "round"})
    ET.SubElement(group, q("polyline"), {"id": f"{obj['id']}-shaft", "points": " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points), **style})
    x1, y1 = points[-2]
    x2, y2 = points[-1]
    angle = math.atan2(y2 - y1, x2 - x1)
    is_normalized = normalized(obj)
    head_length = xy(obj.get("head_length", 0.018 if is_normalized else 16), width, is_normalized, "head_length")
    head_width = xy(obj.get("head_width", 0.016 if is_normalized else 13), height, is_normalized, "head_width")
    bx, by = x2 - head_length * math.cos(angle), y2 - head_length * math.sin(angle)
    px, py = -math.sin(angle) * head_width / 2, math.cos(angle) * head_width / 2
    fill = style.get("stroke", "#536274")
    ET.SubElement(group, q("polygon"), {
        "id": f"{obj['id']}-head",
        "points": f"{fmt(x2)},{fmt(y2)} {fmt(bx + px)},{fmt(by + py)} {fmt(bx - px)},{fmt(by - py)}",
        "fill": fill,
        "stroke": "none",
    })


def add_direct(root: ET.Element, defs: ET.Element, obj: dict[str, Any], width: float, height: float) -> None:
    kind = str(obj["type"]).lower()
    if kind == "arrow":
        add_arrow(root, obj, width, height)
        return
    attrs = base_attrs(obj, "direct-rule")
    if kind in {"line", "connector", "axis", "polyline"}:
        points = points_of(obj, width, height)
        attrs.update(style_of(obj, {"fill": "none", "stroke": "#536274", "stroke_width": "3", "stroke_linecap": "round", "stroke_linejoin": "round"}))
        attrs["points"] = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)
        ET.SubElement(root, q("polyline"), attrs)
        return
    if kind == "polygon":
        points = points_of(obj, width, height)
        attrs.update(style_of(obj, {"fill": "none", "stroke": "#536274", "stroke_width": "2"}))
        attrs["points"] = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in points)
        ET.SubElement(root, q("polygon"), attrs)
        return
    x, y, w, h = bbox_of(obj, width, height)
    if kind in {"circle", "ellipse"}:
        attrs.update(style_of(obj, {"fill": "none", "stroke": "#536274", "stroke_width": "2"}))
        attrs.update({"cx": fmt(x + w / 2), "cy": fmt(y + h / 2)})
        if kind == "circle":
            attrs["r"] = fmt(min(w, h) / 2)
        else:
            attrs.update({"rx": fmt(w / 2), "ry": fmt(h / 2)})
        ET.SubElement(root, q(kind), attrs)
        return
    defaults = {"fill": "none", "stroke": "#536274", "stroke_width": "2"}
    if kind in {"background", "region", "heatmap", "gradient_legend"}:
        defaults = {"fill": "#ffffff", "stroke": "none"}
    attrs.update(style_of(obj, defaults))
    apply_gradient(defs, obj, attrs)
    attrs.update({"x": fmt(x), "y": fmt(y), "width": fmt(w), "height": fmt(h)})
    if kind in {"frame", "rounded_rect", "region"}:
        radius = obj.get("rx", obj.get("radius", 0.012 if normalized(obj) else 12))
        attrs["rx"] = fmt(xy(radius, width, normalized(obj), "rx"))
        attrs["ry"] = fmt(xy(obj.get("ry", radius), height, normalized(obj), "ry"))
    ET.SubElement(root, q("rect"), attrs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-manifest", required=True, type=Path)
    parser.add_argument("--output-svg", required=True, type=Path)
    args = parser.parse_args()
    manifest_path = args.scene_manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    width, height = canvas_of(manifest)
    root = ET.Element(q("svg"), {
        "width": fmt(width), "height": fmt(height), "viewBox": f"0 0 {fmt(width)} {fmt(height)}",
        "data-illustrator-flowchart-mode": "hybrid-scene-manifest",
    })
    defs = ET.SubElement(root, q("defs"))
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scene manifest objects must be an array")
    for obj in sorted(objects, key=lambda item: int(item.get("draw_order", item.get("z_index", 0)))):
        if not isinstance(obj, dict) or not obj.get("id") or not obj.get("type"):
            raise ValueError("every object requires id and type")
        if str(obj["type"]).lower() in SEMANTIC_TYPES:
            add_semantic_asset(root, defs, obj, manifest_path.parent, width, height)
        else:
            add_direct(root, defs, obj, width, height)
    output = args.output_svg.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output, encoding="utf-8", xml_declaration=True)
    print(json.dumps({"ok": True, "output_svg": str(output), "object_count": len(objects)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"HYBRID_BUILD_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
