#!/usr/bin/env python3
"""Add SAM3 foreground clip contours to complex Scene Manifest assets."""

from __future__ import annotations

import argparse
import base64
import json
import math
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


SEMANTIC_TYPES = {"semantic_asset", "asset", "subject"}


def run_checked(command: list[str], timeout: int = 300) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
    return result.stdout


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def raw_gray(mask_png: Path, width: int, height: int, magick: str) -> list[bool]:
    raw_path = mask_png.with_suffix(".gray")
    run_checked([magick, str(mask_png), "-colorspace", "Gray", "-depth", "8", f"gray:{raw_path}"])
    payload = raw_path.read_bytes()
    raw_path.unlink(missing_ok=True)
    if len(payload) != width * height:
        raise ValueError(f"Unexpected mask byte count: {len(payload)} != {width * height}")
    return [value >= 128 for value in payload]


def polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )) / 2


def collinear_simplify(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if len(points) < 4:
        return points
    result: list[tuple[int, int]] = []
    for index, point in enumerate(points):
        previous = points[index - 1]
        following = points[(index + 1) % len(points)]
        first = (point[0] - previous[0], point[1] - previous[1])
        second = (following[0] - point[0], following[1] - point[1])
        if first[0] * second[1] != first[1] * second[0]:
            result.append(point)
    return result


def point_line_distance(point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> float:
    if start == end:
        return math.dist(point, start)
    dx, dy = end[0] - start[0], end[1] - start[1]
    return abs(dy * point[0] - dx * point[1] + end[0] * start[1] - end[1] * start[0]) / math.hypot(dx, dy)


def rdp(points: list[tuple[int, int]], epsilon: float) -> list[tuple[int, int]]:
    if len(points) <= 2:
        return points
    distances = [point_line_distance(point, points[0], points[-1]) for point in points[1:-1]]
    maximum = max(distances, default=0)
    if maximum <= epsilon:
        return [points[0], points[-1]]
    index = distances.index(maximum) + 1
    return rdp(points[: index + 1], epsilon)[:-1] + rdp(points[index:], epsilon)


def simplify_closed(points: list[tuple[int, int]], epsilon: float) -> list[tuple[int, int]]:
    points = collinear_simplify(points)
    if len(points) < 5:
        return points
    anchor = 0
    farthest = max(range(1, len(points)), key=lambda index: math.dist(points[anchor], points[index]))
    first = rdp(points[anchor : farthest + 1], epsilon)
    second = rdp(points[farthest:] + [points[anchor]], epsilon)
    return (first[:-1] + second[:-1])


def trace_contours(mask: list[bool], width: int, height: int, minimum_area: int, epsilon: float) -> list[list[list[float]]]:
    outgoing: dict[tuple[int, int], list[tuple[int, int]]] = {}

    def foreground(x: int, y: int) -> bool:
        return 0 <= x < width and 0 <= y < height and mask[y * width + x]

    def add(start: tuple[int, int], end: tuple[int, int]) -> None:
        outgoing.setdefault(start, []).append(end)

    for y in range(height):
        for x in range(width):
            if not foreground(x, y):
                continue
            if not foreground(x, y - 1):
                add((x, y), (x + 1, y))
            if not foreground(x + 1, y):
                add((x + 1, y), (x + 1, y + 1))
            if not foreground(x, y + 1):
                add((x + 1, y + 1), (x, y + 1))
            if not foreground(x - 1, y):
                add((x, y + 1), (x, y))

    contours: list[list[list[float]]] = []
    while outgoing:
        start = next(iter(outgoing))
        current = start
        polygon: list[tuple[int, int]] = [start]
        for _ in range((width + 1) * (height + 1) * 2):
            candidates = outgoing.get(current)
            if not candidates:
                break
            following = candidates.pop()
            if not candidates:
                outgoing.pop(current, None)
            current = following
            if current == start:
                break
            polygon.append(current)
        if current != start or len(polygon) < 3:
            continue
        polygon = simplify_closed(polygon, epsilon)
        if len(polygon) < 3 or polygon_area([(float(x), float(y)) for x, y in polygon]) < minimum_area:
            continue
        contours.append([[round(x / width, 6), round(y / height, 6)] for x, y in polygon])
    return contours


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-manifest", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    parser.add_argument("--mask-dir", required=True, type=Path)
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--remote-port", type=int, default=8765)
    parser.add_argument("--minimum-area", type=int, default=16)
    parser.add_argument("--simplify", type=float, default=1.25)
    args = parser.parse_args()
    magick = shutil.which("magick") or shutil.which("convert")
    curl = shutil.which("curl")
    if not magick or not curl:
        raise RuntimeError("ImageMagick and curl are required")
    manifest_path = args.scene_manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scene manifest objects must be an array")
    mask_dir = args.mask_dir.resolve()
    mask_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    tunnel = subprocess.Popen([
        "ssh", "-N", "-o", "ExitOnForwardFailure=yes", "-L",
        f"127.0.0.1:{port}:127.0.0.1:{args.remote_port}", args.ssh_target,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        for _ in range(120):
            if tunnel.poll() is not None:
                raise RuntimeError((tunnel.stderr.read() if tunnel.stderr else "") or "SSH tunnel exited")
            health = subprocess.run([curl, "-fsS", f"http://127.0.0.1:{port}/health"], capture_output=True, text=True)
            if health.returncode == 0:
                break
            time.sleep(1)
        else:
            raise TimeoutError("SAM3 health check timed out")

        reports: dict[str, Any] = {}
        for obj in objects:
            if not isinstance(obj, dict) or str(obj.get("type") or "").lower() not in SEMANTIC_TYPES:
                continue
            if obj.get("segmentation_mode") == "skip":
                reports[str(obj["id"])] = {"provider": "sam3", "status": "skipped-by-manifest"}
                continue
            crop = Path(str(obj.get("asset_crop") or ""))
            if not crop.is_absolute():
                crop = manifest_path.parent / crop
            crop = crop.resolve(strict=True)
            identify = run_checked([magick, "identify", "-format", "%w %h", str(crop)])
            width, height = (int(part) for part in identify.split())
            prompts = obj.get("sam3_prompts")
            if isinstance(prompts, str):
                prompts = [prompts]
            if isinstance(prompts, list) and prompts:
                prompt_text = ",".join(str(item) for item in prompts)
                response = run_checked([
                    curl, "-fsS", "-F", f"image=@{crop}", "-F", f"prompts={prompt_text}",
                    "-F", "return_masks=true", "-F", f"min_score={float(obj.get('sam3_min_score', 0.1))}",
                    f"http://127.0.0.1:{port}/segment",
                ], timeout=600)
                payload = json.loads(response)
                candidates = [item for item in (payload.get("results") or []) if item.get("mask_b64") and int(item.get("mask_pixels") or 0) > 0]
                results = []
                prompt_limits = obj.get("sam3_prompt_limits") if isinstance(obj.get("sam3_prompt_limits"), dict) else {}
                for prompt in prompts:
                    matching = [item for item in candidates if item.get("prompt") == str(prompt)]
                    if matching:
                        limit = max(1, int(prompt_limits.get(str(prompt), 1)))
                        results.extend(sorted(matching, key=lambda item: float(item.get("score") or 0), reverse=True)[:limit])
                converted_boxes = []
            else:
                raw_boxes = obj.get("sam3_boxes")
                if isinstance(raw_boxes, list) and raw_boxes:
                    converted_boxes = []
                    for box in raw_boxes:
                        if not isinstance(box, (list, tuple)) or len(box) != 4:
                            raise ValueError(f"{obj['id']} has an invalid sam3 box")
                        converted_boxes.append([
                            round(float(box[0]) * width), round(float(box[1]) * height),
                            round(float(box[2]) * width), round(float(box[3]) * height),
                        ])
                else:
                    margin = int(obj.get("sam3_box_margin_px", max(2, round(min(width, height) * 0.03))))
                    converted_boxes = [[margin, margin, width - margin, height - margin]]
                boxes = json.dumps(converted_boxes)
                response = run_checked([
                    curl, "-fsS", "-F", f"image=@{crop}", "-F", f"boxes={boxes}",
                    f"http://127.0.0.1:{port}/segment_bbox",
                ], timeout=600)
                payload = json.loads(response)
                results = payload.get("results") or []
            if not results:
                if obj.get("segmentation_optional"):
                    reports[str(obj["id"])] = {"provider": "sam3", "status": "skipped-empty-optional"}
                    continue
                raise RuntimeError(f"SAM3 returned no mask for {obj['id']}")
            result = results[0]
            mask_width, mask_height = map(int, result.get("mask_size") or payload.get("image_size") or [width, height])
            combined_mask = [False] * (mask_width * mask_height)
            for result_index, item in enumerate(results):
                item_png = mask_dir / f".{obj['id']}-{result_index}.png"
                item_png.write_bytes(base64.b64decode(item["mask_b64"]))
                item_mask = raw_gray(item_png, mask_width, mask_height, magick)
                combined_mask = [first or second for first, second in zip(combined_mask, item_mask)]
                item_png.unlink(missing_ok=True)
            mask = combined_mask
            raw_mask = bytes(255 if value else 0 for value in mask)
            # Write a portable PGM preview without adding a Pillow dependency.
            (mask_dir / f"{obj['id']}.pgm").write_bytes(
                f"P5\n{mask_width} {mask_height}\n255\n".encode("ascii") + raw_mask
            )
            contours = trace_contours(mask, mask_width, mask_height, args.minimum_area, args.simplify)
            if not contours:
                if obj.get("segmentation_optional"):
                    reports[str(obj["id"])] = {"provider": "sam3", "status": "skipped-empty-optional"}
                    continue
                raise RuntimeError(f"SAM3 mask produced no usable contour for {obj['id']}")
            obj["clip_contours"] = contours
            obj["segmentation"] = {
                "provider": "sam3", "purpose": "foreground-clip-only",
                "confidence": max((item.get("confidence") or item.get("score") or 0) for item in results),
                "iou_score": max((item.get("iou_score") or 0) for item in results),
                "mask_pixels": sum(mask), "contour_count": len(contours),
                "box_count": len(converted_boxes), "prompts": prompts if isinstance(prompts, list) else None,
            }
            reports[str(obj["id"])] = obj["segmentation"]
    finally:
        tunnel.terminate()
        try:
            tunnel.wait(timeout=5)
        except subprocess.TimeoutExpired:
            tunnel.kill()

    output = args.output_manifest.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (mask_dir / "sam3-report.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_manifest": str(output), "segmented_assets": len(reports)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SAM3_SCENE_SEGMENT_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
