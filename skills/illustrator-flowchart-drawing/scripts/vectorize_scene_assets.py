#!/usr/bin/env python3
"""Crop and vectorize only semantic assets declared by a Scene Manifest."""

from __future__ import annotations

import argparse
from collections import Counter
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


def estimate_border_background(image: Image.Image) -> tuple[int, int, int]:
    """Estimate a flat local background from quantized border pixels."""
    rgb = image.convert("RGB")
    border = max(1, min(rgb.width, rgb.height) // 24)
    pixels: list[tuple[int, int, int]] = []
    for y in range(rgb.height):
        for x in range(rgb.width):
            if x < border or x >= rgb.width - border or y < border or y >= rgb.height - border:
                pixels.append(rgb.getpixel((x, y)))
    quantized = Counter(tuple(min(255, (channel // 8) * 8 + 4) for channel in pixel) for pixel in pixels)
    return quantized.most_common(1)[0][0] if quantized else (255, 255, 255)


def transparent_foreground_crop(
    image: Image.Image,
    background: tuple[int, int, int],
    tolerance: float,
    feather: float,
) -> Image.Image:
    """Color-key the local panel background while keeping a white model matte in hidden RGB."""
    source = image.convert("RGB")
    result = Image.new("RGBA", source.size, (255, 255, 255, 0))
    output = []
    for red, green, blue in source.getdata():
        distance = math.dist((red, green, blue), background)
        if distance <= tolerance:
            alpha = 0
        elif feather > 0 and distance < tolerance + feather:
            alpha = round(255 * (distance - tolerance) / feather)
        else:
            alpha = 255
        # The private SuperSVG loader currently converts to RGB. Premultiply onto
        # white so transparent panel color never becomes model-visible content.
        ratio = alpha / 255.0
        output.append((
            round(red * ratio + 255 * (1 - ratio)),
            round(green * ratio + 255 * (1 - ratio)),
            round(blue * ratio + 255 * (1 - ratio)),
            alpha,
        ))
    result.putdata(output)
    return result


def white_matte_rgba(image: Image.Image) -> Image.Image:
    """Preserve alpha for audit while making transparent RGB safe for an RGB-only model loader."""
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    matte = Image.new("RGB", rgba.size, "white")
    matte.paste(rgba.convert("RGB"), mask=alpha)
    result = matte.convert("RGBA")
    result.putalpha(alpha)
    return result


def trim_transparent_margin(image: Image.Image) -> Image.Image:
    """Trim excessive empty canvas while retaining a small transparent safety margin."""
    rgba = image.convert("RGBA")
    alpha_bbox = rgba.getchannel("A").getbbox()
    if alpha_bbox is None:
        raise ValueError("enhanced image contains no visible pixels")
    left, top, right, bottom = alpha_bbox
    padding = max(2, round(max(right - left, bottom - top) * 0.025))
    return rgba.crop((
        max(0, left - padding),
        max(0, top - padding),
        min(rgba.width, right + padding),
        min(rgba.height, bottom + padding),
    ))


def accepted_enhancement(
    obj: dict[str, Any],
    manifest_root: Path,
    asset_dir: Path,
    object_id: str,
) -> tuple[Image.Image, Path, tuple[int, int]] | None:
    """Load an audited ChatGPT-web result and make a job-local provenance copy."""
    record = obj.get("source_enhancement")
    if not isinstance(record, dict) or str(record.get("semantic_audit", "")).lower() != "accepted":
        return None
    if record.get("provider") != "chatgpt-web-imagegen" or record.get("mode") != "web":
        raise ValueError(f"{object_id} accepted enhancement must use chatgpt-web-imagegen in web mode")
    if record.get("client") != "leeguooooo/chatgpt-imagegen":
        raise ValueError(f"{object_id} accepted enhancement must record client leeguooooo/chatgpt-imagegen")
    if record.get("transparent_rgba") is not True:
        raise ValueError(f"{object_id} accepted enhancement must declare transparent_rgba true")
    generated_value = record.get("generated_png")
    if not isinstance(generated_value, str) or not generated_value.strip():
        raise ValueError(f"{object_id} accepted enhancement requires generated_png")
    generated_path = Path(generated_value).expanduser()
    if not generated_path.is_absolute():
        generated_path = manifest_root / generated_path
    generated_path = generated_path.resolve(strict=True)
    with Image.open(generated_path) as opened:
        if "A" not in opened.getbands():
            raise ValueError(f"{object_id} enhanced PNG has no alpha channel")
        rgba = opened.convert("RGBA")
    alpha_min, alpha_max = rgba.getchannel("A").getextrema()
    if alpha_min >= 255:
        raise ValueError(f"{object_id} enhanced PNG is fully opaque rather than transparent")
    if alpha_max <= 0:
        raise ValueError(f"{object_id} enhanced PNG is fully transparent")
    local_copy = asset_dir / f"{object_id}-enhanced-source.png"
    rgba.save(local_copy)
    record["workspace_copy"] = str(local_copy)
    record["alpha_extrema"] = [alpha_min, alpha_max]
    record["transparent_rgba"] = True
    return trim_transparent_margin(rgba), local_copy, (alpha_min, alpha_max)


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
    parser.add_argument("--background-tolerance", type=float, default=24.0)
    parser.add_argument("--background-feather", type=float, default=12.0)
    parser.add_argument("--matte-vector-tolerance", type=float, default=16.0)
    parser.add_argument("--matte-neutral-luminance", type=float, default=0.82)
    parser.add_argument("--matte-neutral-chroma", type=float, default=28.0)
    parser.add_argument("--crop-only", action="store_true")
    parser.add_argument("--per-asset", action="store_true", help="Compatibility mode that reloads SuperSVG for every asset")
    args = parser.parse_args()

    if args.path_num < 1000:
        parser.error("quality mode requires --path-num >= 1000")
    if args.optimize_iter < 10:
        parser.error("quality mode requires --optimize-iter >= 10")
    if args.rows < 1 or args.cols < 1 or args.overlap < 0:
        parser.error("invalid SuperSVG tiling settings")
    if min(args.background_tolerance, args.background_feather, args.matte_vector_tolerance, args.matte_neutral_chroma) < 0:
        parser.error("background tolerances must be non-negative")
    if not 0 <= args.matte_neutral_luminance <= 1:
        parser.error("matte neutral luminance must be between 0 and 1")

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
        source_crop_path = asset_dir / f"{object_id}-source.png"
        svg_path = asset_dir / f"{object_id}.svg"
        state_path = asset_dir / f"{object_id}.remote-job.json"
        original_crop = source_image.crop((left, top, left + crop_width, top + crop_height))
        original_crop.save(source_crop_path)
        enhancement = accepted_enhancement(obj, manifest_path.parent, asset_dir, object_id)
        crop_image = enhancement[0] if enhancement else original_crop
        background_policy = str(obj.get("background_policy", "transparent")).lower()
        if background_policy not in {"transparent", "preserve"}:
            raise ValueError(f"{object_id} background_policy must be transparent or preserve")
        if enhancement and background_policy != "transparent":
            raise ValueError(f"{object_id} ChatGPT web enhancement requires background_policy transparent")
        background = (255, 255, 255) if enhancement else estimate_border_background(crop_image)
        if enhancement:
            crop_image = white_matte_rgba(crop_image)
        elif background_policy == "transparent":
            crop_image = transparent_foreground_crop(
                crop_image,
                background,
                float(obj.get("background_tolerance", args.background_tolerance)),
                float(obj.get("background_feather", args.background_feather)),
            )
        if args.border_px > 0:
            fill = (255, 255, 255, 0) if crop_image.mode == "RGBA" else "white"
            crop_image = ImageOps.expand(crop_image, border=args.border_px, fill=fill)
        crop_image.save(crop_path)
        obj["crop"] = {"x": left, "y": top, "width": crop_width, "height": crop_height}
        obj["asset_crop"] = str(crop_path)
        obj["asset_source_crop"] = str(source_crop_path)
        obj["background_removal"] = {
            "policy": background_policy,
            "source": "chatgpt-web-alpha" if enhancement else "local-border-key",
            "estimated_rgb": list(background),
            "model_matte": "#ffffff",
            "raster_tolerance": float(obj.get("background_tolerance", args.background_tolerance)),
            "feather": float(obj.get("background_feather", args.background_feather)),
        }
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
        if background_policy == "transparent":
            matte_report = asset_dir / f"{object_id}.matte-removal.json"
            run_checked([
                sys.executable, str(scripts / "strip_vector_matte.py"),
                "--svg", str(svg_path), "--matte", "#ffffff",
                "--tolerance", str(float(obj.get("matte_vector_tolerance", args.matte_vector_tolerance))),
                "--neutral-luminance", str(float(obj.get("matte_neutral_luminance", args.matte_neutral_luminance))),
                "--neutral-chroma", str(float(obj.get("matte_neutral_chroma", args.matte_neutral_chroma))),
                "--foreground-mask", str(crop_path),
                "--max-pale-area", str(float(obj.get("matte_max_pale_area", 0.12))),
                "--report", str(matte_report),
            ])
        run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(svg_path)])
        obj["asset_svg"] = str(svg_path)
        obj["source"] = {"provider": "supersvg", "scope": "complex-asset-crop"}
        obj["status"] = "accepted"
        obj["vector_valid"] = True
        obj["background_transparent"] = background_policy == "transparent"
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
            if str(obj.get("background_policy", "transparent")).lower() == "transparent":
                matte_report = asset_dir / f"{obj['id']}.matte-removal.json"
                run_checked([
                    sys.executable, str(scripts / "strip_vector_matte.py"),
                    "--svg", str(svg_path), "--matte", "#ffffff",
                    "--tolerance", str(float(obj.get("matte_vector_tolerance", args.matte_vector_tolerance))),
                    "--neutral-luminance", str(float(obj.get("matte_neutral_luminance", args.matte_neutral_luminance))),
                    "--neutral-chroma", str(float(obj.get("matte_neutral_chroma", args.matte_neutral_chroma))),
                    "--foreground-mask", str(asset_dir / f"{obj['id']}.png"),
                    "--max-pale-area", str(float(obj.get("matte_max_pale_area", 0.12))),
                    "--report", str(matte_report),
                ])
            run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(svg_path)])
            obj["asset_svg"] = str(svg_path)
            obj["source"] = {"provider": "supersvg", "scope": "complex-asset-crop", "batch_job_id": job_id}
            obj["status"] = "accepted"
            obj["vector_valid"] = True
            obj["background_transparent"] = str(obj.get("background_policy", "transparent")).lower() == "transparent"
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
