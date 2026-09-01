#!/usr/bin/env python3
"""Crop and vectorize only semantic assets declared by a Scene Manifest."""

from __future__ import annotations

import argparse
import json
import math
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


SEMANTIC_TYPES = {"semantic_asset", "asset", "subject"}


def run_checked(command: list[str], timeout: int | None = None) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
    return result.stdout.strip()


def finite(value: Any, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def pixel_bbox(obj: dict[str, Any], image_width: int, image_height: int) -> tuple[int, int, int, int]:
    bbox = obj.get("bbox_normalized") or obj.get("normalized_bbox") or obj.get("bbox")
    if not isinstance(bbox, dict):
        raise ValueError(f"{obj.get('id')} requires bbox")
    normalized = "bbox_normalized" in obj or "normalized_bbox" in obj or obj.get("coordinate_space", "normalized") == "normalized"
    x = finite(bbox.get("x"), "bbox.x")
    y = finite(bbox.get("y"), "bbox.y")
    width = finite(bbox.get("width"), "bbox.width")
    height = finite(bbox.get("height"), "bbox.height")
    if normalized:
        x, width = x * image_width, width * image_width
        y, height = y * image_height, height * image_height
    padding = int(obj.get("crop_padding_px", 8))
    left = max(0, math.floor(x) - padding)
    top = max(0, math.floor(y) - padding)
    right = min(image_width, math.ceil(x + width) + padding)
    bottom = min(image_height, math.ceil(y + height) + padding)
    if right <= left or bottom <= top:
        raise ValueError(f"{obj.get('id')} has an empty crop")
    return left, top, right - left, bottom - top


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--scene-manifest", required=True, type=Path)
    parser.add_argument("--output-manifest", required=True, type=Path)
    parser.add_argument("--asset-dir", required=True, type=Path)
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--remote-root", default="services/supersvg-eval")
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--cols", type=int, default=1)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--path-num", type=int, default=1600)
    parser.add_argument("--optimize-iter", type=int, default=14)
    parser.add_argument("--refine-batch-size", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--border-px", type=int, default=0)
    parser.add_argument("--crop-only", action="store_true")
    parser.add_argument("--per-asset", action="store_true", help="Compatibility mode that reloads SuperSVG for every asset")
    args = parser.parse_args()

    if args.path_num < 1000:
        parser.error("quality mode requires --path-num >= 1000")
    if args.optimize_iter < 10:
        parser.error("quality mode requires --optimize-iter >= 10")
    if args.rows < 1 or args.cols < 1 or args.overlap < 0:
        parser.error("invalid SuperSVG tiling settings")

    image = args.input_image.resolve(strict=True)
    manifest_path = args.scene_manifest.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scene manifest objects must be an array")
    source_image = Image.open(image).convert("RGB")
    image_width, image_height = source_image.size
    asset_dir = args.asset_dir.resolve()
    asset_dir.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    vectorized = 0
    semantic_objects: list[dict[str, Any]] = []

    for obj in objects:
        if not isinstance(obj, dict) or str(obj.get("type") or "").lower() not in SEMANTIC_TYPES:
            continue
        semantic_objects.append(obj)
        object_id = str(obj.get("id") or "")
        if not object_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in object_id):
            raise ValueError("semantic asset ids may contain only letters, numbers, '-' and '_'")
        left, top, crop_width, crop_height = pixel_bbox(obj, image_width, image_height)
        crop_path = asset_dir / f"{object_id}.png"
        svg_path = asset_dir / f"{object_id}.svg"
        state_path = asset_dir / f"{object_id}.remote-job.json"
        crop_image = source_image.crop((left, top, left + crop_width, top + crop_height))
        if args.border_px > 0:
            crop_image = ImageOps.expand(crop_image, border=args.border_px, fill="white")
        crop_image.save(crop_path)
        obj["crop"] = {"x": left, "y": top, "width": crop_width, "height": crop_height}
        obj["asset_crop"] = str(crop_path)
        if args.crop_only:
            continue
        if not args.per_asset:
            continue
        profile = obj.get("vector_profile") if isinstance(obj.get("vector_profile"), dict) else {}
        profile_path_num = int(profile.get("path_num", args.path_num))
        profile_optimize_iter = int(profile.get("optimize_iter", args.optimize_iter))
        if profile_path_num < 1000 or profile_optimize_iter < 10:
            raise ValueError(f"{object_id} vector_profile falls below the quality floor")
        command = [
            sys.executable, str(scripts / "supersvg_remote.py"),
            "--input", str(crop_path), "--output", str(svg_path), "--state", str(state_path),
            "--ssh-target", args.ssh_target, "--remote-root", args.remote_root,
            "--gpu-index", str(args.gpu_index),
            "--rows", str(int(profile.get("rows", args.rows))),
            "--cols", str(int(profile.get("cols", args.cols))),
            "--overlap", str(int(profile.get("overlap", args.overlap))),
            "--path-num", str(profile_path_num),
            "--optimize-iter", str(profile_optimize_iter),
            "--refine-batch-size", str(int(profile.get("refine_batch_size", args.refine_batch_size))),
            "--timeout", str(args.timeout),
        ]
        run_checked(command, timeout=args.timeout + 600)
        run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(svg_path)])
        obj["asset_svg"] = str(svg_path)
        obj["source"] = {"provider": "supersvg", "scope": "complex-asset-crop"}
        obj["status"] = "accepted"
        obj["vector_valid"] = True
        vectorized += 1

    if semantic_objects and not args.crop_only and not args.per_asset:
        job_id = f"illustrator-flowchart-assets-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        remote_job = f"{args.remote_root.rstrip('/')}/jobs/{job_id}"
        remote_input = f"{remote_job}/input"
        remote_output = f"{remote_job}/output"
        mkdir_command = "mkdir -p " + " ".join(shlex.quote(path) for path in (remote_input, remote_output))
        run_checked(["ssh", args.ssh_target, mkdir_command], timeout=60)
        crop_paths = [asset_dir / f"{obj['id']}.png" for obj in semantic_objects]
        run_checked(["scp", *[str(path) for path in crop_paths], f"{args.ssh_target}:{remote_input}/"], timeout=600)
        path_num = max(
            [args.path_num]
            + [int((obj.get("vector_profile") or {}).get("path_num", args.path_num)) for obj in semantic_objects]
        )
        optimize_iter = max(
            [args.optimize_iter]
            + [int((obj.get("vector_profile") or {}).get("optimize_iter", args.optimize_iter)) for obj in semantic_objects]
        )
        refine_batch_size = max(
            [args.refine_batch_size]
            + [int((obj.get("vector_profile") or {}).get("refine_batch_size", args.refine_batch_size)) for obj in semantic_objects]
        )
        batch_script = f"{args.remote_root.rstrip('/')}/SuperSVG/supersvg_asset_batch.py"
        python_path = f"{args.remote_root.rstrip('/')}/.venv/bin/python"
        remote_command = " ".join(shlex.quote(part) for part in [
            "env", f"CUDA_VISIBLE_DEVICES={args.gpu_index}", python_path, batch_script,
            "--input-dir", remote_input,
            "--output-dir", remote_output,
            "--rows", str(args.rows),
            "--cols", str(args.cols),
            "--overlap", str(args.overlap),
            "--path-num", str(path_num),
            "--optimize-iter", str(optimize_iter),
            "--refine-batch-size", str(refine_batch_size),
            "--device", "cuda",
        ])
        run_checked(["ssh", args.ssh_target, remote_command], timeout=args.timeout)
        run_checked(["scp", f"{args.ssh_target}:{remote_output}/*.svg", str(asset_dir)], timeout=600)
        for obj in semantic_objects:
            svg_path = asset_dir / f"{obj['id']}.svg"
            run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(svg_path)])
            obj["asset_svg"] = str(svg_path)
            obj["source"] = {"provider": "supersvg", "scope": "complex-asset-crop", "batch_job_id": job_id}
            obj["status"] = "accepted"
            obj["vector_valid"] = True
            vectorized += 1
        (asset_dir / "batch-remote-job.json").write_text(json.dumps({
            "schema_version": "1.0",
            "provider": "supersvg",
            "model": "JTUplayer/SuperSVG",
            "job_id": job_id,
            "remote_job_dir": remote_job,
            "asset_count": len(semantic_objects),
            "rows": args.rows,
            "cols": args.cols,
            "overlap": args.overlap,
            "path_num_per_asset": path_num,
            "optimize_iter": optimize_iter,
            "refine_batch_size": refine_batch_size,
            "status": "completed",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output = args.output_manifest.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    validation_command = [sys.executable, str(scripts / "validate_scene_manifest.py"), "--manifest", str(output)]
    if args.crop_only:
        validation_command.append("--allow-unresolved-assets")
    run_checked(validation_command)
    print(json.dumps({
        "ok": True,
        "output_manifest": str(output),
        "semantic_assets_vectorized": vectorized,
        "crop_only": args.crop_only,
        "direct_elements_not_sent_to_model": len(objects) - vectorized,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SCENE_ASSET_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
