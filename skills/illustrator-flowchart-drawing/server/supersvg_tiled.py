#!/usr/bin/env python3
"""Run SuperSVG on aspect-preserving overlapping tiles and stitch the SVG paths."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--cols", type=int, default=1)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--path-num", type=int, default=1600)
    parser.add_argument("--optimize-iter", type=int, default=14)
    parser.add_argument("--refine-batch-size", type=int, default=8)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.rows < 1 or args.cols < 1 or args.overlap < 0:
        parser.error("invalid tiling settings")
    if args.path_num < 1000 or args.optimize_iter < 10:
        parser.error("quality mode requires path-num >= 1000 and optimize-iter >= 10")
    return args


def split_edges(length: int, parts: int) -> list[int]:
    return [round(i * length / parts) for i in range(parts + 1)]


def background_rgb(image: Image.Image) -> tuple[int, int, int]:
    """Estimate the border background without trusting decorated corners."""
    border = max(2, min(image.width, image.height) // 160)
    pixels = []
    for y in range(image.height):
        for x in range(image.width):
            if x < border or x >= image.width - border or y < border or y >= image.height - border:
                pixels.append(image.getpixel((x, y)))
    quantized = Counter(tuple(min(255, (channel // 16) * 16 + 8) for channel in pixel) for pixel in pixels)
    if quantized:
        return quantized.most_common(1)[0][0]
    return tuple(round(statistics.median(px[channel] for px in pixels)) for channel in range(3))


def crop_with_background(
    image: Image.Image,
    bounds: tuple[int, int, int, int],
    fill: tuple[int, int, int],
) -> Image.Image:
    """Crop including out-of-image margins, filled with the estimated background."""
    x0, y0, x1, y1 = bounds
    canvas = Image.new("RGB", (x1 - x0, y1 - y0), fill)
    source_x0, source_y0 = max(0, x0), max(0, y0)
    source_x1, source_y1 = min(image.width, x1), min(image.height, y1)
    if source_x1 > source_x0 and source_y1 > source_y0:
        source = image.crop((source_x0, source_y0, source_x1, source_y1))
        canvas.paste(source, (source_x0 - x0, source_y0 - y0))
    return canvas


def prepare_tiles(image_path: Path, tiles_dir: Path, rows: int, cols: int, overlap: int) -> dict:
    image = Image.open(image_path).convert("RGB")
    tiles_dir.mkdir(parents=True, exist_ok=True)
    x_edges = split_edges(image.width, cols)
    y_edges = split_edges(image.height, rows)
    fill = background_rgb(image)
    tiles = []

    for row in range(rows):
        for col in range(cols):
            core_x0, core_x1 = x_edges[col], x_edges[col + 1]
            core_y0, core_y1 = y_edges[row], y_edges[row + 1]
            # Keep a real overlap margin even along the outside image edges.
            # Without it, subjects near the right/bottom boundary are generated
            # against a hard tile edge and may be pushed outside the final clip.
            crop_x0 = core_x0 - overlap
            crop_y0 = core_y0 - overlap
            crop_x1 = core_x1 + overlap
            crop_y1 = core_y1 + overlap
            crop = crop_with_background(image, (crop_x0, crop_y0, crop_x1, crop_y1), fill)
            square = max(crop.width, crop.height)
            pad_left = (square - crop.width) // 2
            pad_top = (square - crop.height) // 2
            canvas = Image.new("RGB", (square, square), fill)
            canvas.paste(crop, (pad_left, pad_top))
            name = f"tile-r{row:02d}-c{col:02d}"
            tile_path = tiles_dir / f"{name}.png"
            canvas.save(tile_path)
            tiles.append(
                {
                    "name": name,
                    "core": [core_x0, core_y0, core_x1, core_y1],
                    "crop": [crop_x0, crop_y0, crop_x1, crop_y1],
                    "square": square,
                    "pad_left": pad_left,
                    "pad_top": pad_top,
                }
            )

    manifest = {
        "source": str(image_path),
        "width": image.width,
        "height": image.height,
        "rows": rows,
        "cols": cols,
        "overlap": overlap,
        "background": fill,
        "tiles": tiles,
    }
    return manifest


def stitch(manifest: dict, vector_dir: Path, output_svg: Path) -> None:
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "version": "1.1",
            "width": str(manifest["width"]),
            "height": str(manifest["height"]),
            "viewBox": f'0 0 {manifest["width"]} {manifest["height"]}',
        },
    )
    defs = ET.SubElement(root, f"{{{SVG_NS}}}defs")

    for tile in manifest["tiles"]:
        core_x0, core_y0, core_x1, core_y1 = tile["core"]
        clip_id = f'clip-{tile["name"]}'
        clip = ET.SubElement(defs, f"{{{SVG_NS}}}clipPath", {"id": clip_id})
        ET.SubElement(
            clip,
            f"{{{SVG_NS}}}rect",
            {
                "id": f"{clip_id}-rect",
                "x": str(core_x0),
                "y": str(core_y0),
                "width": str(core_x1 - core_x0),
                "height": str(core_y1 - core_y0),
            },
        )

        tile_svg_path = vector_dir / f'{tile["name"]}.svg'
        tile_root = ET.parse(tile_svg_path).getroot()
        scale = tile["square"] / 512.0
        tx = tile["crop"][0] - tile["pad_left"]
        ty = tile["crop"][1] - tile["pad_top"]
        outer = ET.SubElement(
            root,
            f"{{{SVG_NS}}}g",
            {"id": tile["name"], "clip-path": f"url(#{clip_id})"},
        )
        inner = ET.SubElement(
            outer,
            f"{{{SVG_NS}}}g",
            {"transform": f"matrix({scale:.10g} 0 0 {scale:.10g} {tx} {ty})"},
        )
        editable_index = 0
        for child in list(tile_root):
            if child.tag == f"{{{SVG_NS}}}defs":
                continue
            for element in child.iter():
                local_name = element.tag.rsplit("}", 1)[-1]
                if local_name in {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text"}:
                    editable_index += 1
                    element.set("id", f'{tile["name"]}-{local_name}-{editable_index:04d}')
            inner.append(child)

    output_svg.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_svg, encoding="utf-8", xml_declaration=True)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    tiles_dir = output_dir / "tiles"
    vector_dir = output_dir / "vectors"
    manifest_path = output_dir / "tile-manifest.json"
    stitched_svg = output_dir / f"{args.input.stem}-supersvg-tiled.svg"

    manifest = prepare_tiles(args.input.resolve(), tiles_dir, args.rows, args.cols, args.overlap)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    vector_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "inference.py"),
        "--input_path",
        str(tiles_dir),
        "--output_dir",
        str(vector_dir),
        "--device",
        args.device,
        "--path_num",
        str(args.path_num),
        "--optimize_iter",
        str(args.optimize_iter),
        "--refine_batch_size",
        str(args.refine_batch_size),
    ]
    subprocess.run(command, check=True, cwd=Path(__file__).resolve().parent)
    stitch(manifest, vector_dir, stitched_svg)
    print(stitched_svg)


if __name__ == "__main__":
    main()
