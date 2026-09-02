#!/usr/bin/env python3
"""Remove SuperSVG matte-colored paint paths so complex assets remain transparent."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageFilter


PAINT_TAGS = {"path", "rect", "circle", "ellipse", "polygon", "polyline"}
RGB_RE = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", re.I)
HEX_RE = re.compile(r"#([0-9a-f]{6})", re.I)
NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
TRANSFORM_RE = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def style_map(raw: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in (raw or "").split(";"):
        if ":" in item:
            key, value = item.split(":", 1)
            result[key.strip().lower()] = value.strip()
    return result


def rgb(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    match = RGB_RE.fullmatch(value.strip())
    if match:
        return tuple(max(0, min(255, int(part))) for part in match.groups())  # type: ignore[return-value]
    match = HEX_RE.fullmatch(value.strip())
    if match:
        raw = match.group(1)
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    return None


def opacity_of(element: ET.Element, style: dict[str, str]) -> float:
    try:
        return float(element.get("opacity", style.get("opacity", "1")))
    except ValueError:
        return 1.0


def multiply(a: tuple[float, float, float, float, float, float], b: tuple[float, float, float, float, float, float]) -> tuple[float, float, float, float, float, float]:
    a1,b1,c1,d1,e1,f1 = a
    a2,b2,c2,d2,e2,f2 = b
    return (
        a1*a2+c1*b2, b1*a2+d1*b2, a1*c2+c1*d2, b1*c2+d1*d2,
        a1*e2+c1*f2+e1, b1*e2+d1*f2+f1,
    )


def transform_matrix(raw: str | None) -> tuple[float, float, float, float, float, float]:
    result = (1.0,0.0,0.0,1.0,0.0,0.0)
    for name, payload in TRANSFORM_RE.findall(raw or ""):
        values = [float(value) for value in NUMBER_RE.findall(payload)]
        kind = name.lower()
        if kind == "matrix" and len(values) == 6:
            current = tuple(values)  # type: ignore[assignment]
        elif kind == "translate" and values:
            current = (1.0,0.0,0.0,1.0,values[0],values[1] if len(values)>1 else 0.0)
        elif kind == "scale" and values:
            current = (values[0],0.0,0.0,values[1] if len(values)>1 else values[0],0.0,0.0)
        else:
            continue
        result = multiply(result, current)
    return result


def cumulative_matrix(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> tuple[float, float, float, float, float, float]:
    chain = []
    current: ET.Element | None = element
    while current is not None:
        chain.append(current)
        current = parents.get(current)
    result = (1.0,0.0,0.0,1.0,0.0,0.0)
    for node in reversed(chain):
        result = multiply(result, transform_matrix(node.get("transform")))
    return result


def path_points(element: ET.Element) -> list[tuple[float, float]]:
    tag = local_name(element.tag)
    if tag == "path":
        values = [float(value) for value in NUMBER_RE.findall(element.get("d", ""))]
        return list(zip(values[0::2], values[1::2]))
    if tag in {"polygon", "polyline"}:
        values = [float(value) for value in NUMBER_RE.findall(element.get("points", ""))]
        return list(zip(values[0::2], values[1::2]))
    if tag == "rect":
        x,y,w,h = (float(element.get(k,"0")) for k in ("x","y","width","height"))
        return [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x+w/2,y+h/2)]
    if tag in {"circle", "ellipse"}:
        cx,cy = float(element.get("cx","0")),float(element.get("cy","0"))
        rx = float(element.get("r",element.get("rx","0"))); ry=float(element.get("r",element.get("ry","0")))
        return [(cx,cy),(cx-rx,cy),(cx+rx,cy),(cx,cy-ry),(cx,cy+ry)]
    return []


def foreground_fraction(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    mask: Image.Image,
    view_box: tuple[float, float, float, float],
) -> float | None:
    points = path_points(element)
    if not points:
        return None
    a,b,c,d,e,f = cumulative_matrix(element, parents)
    transformed = [(a*x+c*y+e,b*x+d*y+f) for x,y in points]
    min_x,max_x = min(x for x,_ in transformed),max(x for x,_ in transformed)
    min_y,max_y = min(y for _,y in transformed),max(y for _,y in transformed)
    transformed.extend([
        ((min_x+max_x)/2,(min_y+max_y)/2),
        (min_x,min_y),(max_x,min_y),(max_x,max_y),(min_x,max_y),
    ])
    x0,y0,vw,vh = view_box
    hits = 0
    valid = 0
    for x,y in transformed:
        px = round((x-x0)/vw*(mask.width-1)); py=round((y-y0)/vh*(mask.height-1))
        if 0 <= px < mask.width and 0 <= py < mask.height:
            valid += 1
            if mask.getpixel((px,py)) > 8:
                hits += 1
    return hits/valid if valid else 0.0


def geometry_area_fraction(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    view_box: tuple[float, float, float, float],
) -> float | None:
    points = path_points(element)
    if not points:
        return None
    a,b,c,d,e,f = cumulative_matrix(element, parents)
    transformed = [(a*x+c*y+e,b*x+d*y+f) for x,y in points]
    width = max(x for x,_ in transformed) - min(x for x,_ in transformed)
    height = max(y for _,y in transformed) - min(y for _,y in transformed)
    return max(0.0, width * height / (view_box[2] * view_box[3]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", required=True, type=Path)
    parser.add_argument("--matte", default="#ffffff")
    parser.add_argument("--tolerance", type=float, default=16.0)
    parser.add_argument("--neutral-luminance", type=float, default=0.82)
    parser.add_argument("--neutral-chroma", type=float, default=28.0)
    parser.add_argument("--foreground-mask", type=Path)
    parser.add_argument("--mask-dilation", type=int, default=2)
    parser.add_argument("--min-foreground-fraction", type=float, default=0.08)
    parser.add_argument("--max-pale-area", type=float, default=0.12)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.tolerance < 0:
        parser.error("tolerance must be non-negative")
    if not 0 <= args.neutral_luminance <= 1 or args.neutral_chroma < 0:
        parser.error("neutral thresholds are invalid")
    if args.mask_dilation < 0 or not 0 <= args.min_foreground_fraction <= 1 or not 0 <= args.max_pale_area <= 1:
        parser.error("foreground-mask thresholds are invalid")
    matte = rgb(args.matte)
    if matte is None:
        parser.error("--matte must be #RRGGBB or rgb(r,g,b)")

    svg_path = args.svg.resolve(strict=True)
    tree = ET.parse(svg_path)
    root = tree.getroot()
    parents = {child: parent for parent in root.iter() for child in parent}
    view_values = [float(value) for value in NUMBER_RE.findall(root.get("viewBox", ""))]
    if len(view_values) != 4 or view_values[2] <= 0 or view_values[3] <= 0:
        raise RuntimeError("SVG requires a positive viewBox for foreground filtering")
    view_box = tuple(view_values)  # type: ignore[assignment]
    foreground_mask = None
    if args.foreground_mask:
        foreground_mask = Image.open(args.foreground_mask.resolve(strict=True)).getchannel("A")
        if args.mask_dilation:
            foreground_mask = foreground_mask.filter(ImageFilter.MaxFilter(args.mask_dilation * 2 + 1))
    removed_transparent = 0
    removed_matte = 0
    removed_outside_foreground = 0
    removed_large_pale = 0
    candidates = []
    for element in root.iter():
        if local_name(element.tag) not in PAINT_TAGS:
            continue
        parent = parents.get(element)
        if parent is None or local_name(parent.tag) in {"clipPath", "mask"}:
            continue
        style = style_map(element.get("style"))
        alpha = opacity_of(element, style)
        fill = rgb(element.get("fill") or style.get("fill"))
        if alpha <= 0.001:
            candidates.append((parent, element, "transparent"))
            continue
        if fill is not None:
            luminance = (0.2126 * fill[0] + 0.7152 * fill[1] + 0.0722 * fill[2]) / 255.0
            chroma = max(fill) - min(fill)
            if (
                math.dist(fill, matte) <= args.tolerance
                or (luminance >= args.neutral_luminance and chroma <= args.neutral_chroma)
            ):
                candidates.append((parent, element, "matte"))
                continue
            area_fraction = geometry_area_fraction(element, parents, view_box)
            if area_fraction is not None and area_fraction >= args.max_pale_area and luminance >= 0.76 and chroma <= 75:
                candidates.append((parent, element, "large-pale"))
                continue
        if foreground_mask is not None:
            fraction = foreground_fraction(element, parents, foreground_mask, view_box)
            if fraction is not None and fraction < args.min_foreground_fraction:
                candidates.append((parent, element, "outside-foreground"))

    for parent, element, reason in candidates:
        try:
            parent.remove(element)
        except ValueError:
            continue
        if reason == "transparent":
            removed_transparent += 1
        elif reason == "matte":
            removed_matte += 1
        elif reason == "outside-foreground":
            removed_outside_foreground += 1
        else:
            removed_large_pale += 1

    remaining = sum(1 for element in root.iter() if local_name(element.tag) in PAINT_TAGS)
    if remaining < 1:
        raise RuntimeError("Matte removal deleted every vector paint element")
    temporary = svg_path.with_suffix(svg_path.suffix + ".transparent.tmp")
    tree.write(temporary, encoding="utf-8", xml_declaration=True)
    temporary.replace(svg_path)
    report = {
        "ok": True,
        "svg": str(svg_path),
        "matte": args.matte,
        "tolerance": args.tolerance,
        "neutral_luminance": args.neutral_luminance,
        "neutral_chroma": args.neutral_chroma,
        "removed_matte_elements": removed_matte,
        "removed_zero_opacity_elements": removed_transparent,
        "removed_outside_foreground_elements": removed_outside_foreground,
        "removed_large_pale_elements": removed_large_pale,
        "remaining_paint_elements": remaining,
        "background_transparent": True,
        "foreground_mask": str(args.foreground_mask.resolve()) if args.foreground_mask else None,
        "max_pale_area": args.max_pale_area,
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.resolve().write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
