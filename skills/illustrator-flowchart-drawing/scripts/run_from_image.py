#!/usr/bin/env python3
"""Run the complete object-routed Illustrator流程图绘制 pipeline with private SuperSVG assets."""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


NAME_RE = re.compile(r"^illustrator-flowchart-(\d+)(?:\.|$)", re.IGNORECASE)
SEMANTIC_TYPES = {"semantic_asset", "asset", "subject"}


def run_checked(command: list[str], timeout: int | None = None) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
    return result.stdout.strip()


def reserve_job_directory(root: Path) -> tuple[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    used: set[int] = set()
    for path in root.iterdir():
        match = NAME_RE.match(path.name)
        if match:
            used.add(int(match.group(1)))
    candidate = max(used, default=0) + 1
    for number in range(candidate, candidate + 1000):
        name = f"illustrator-flowchart-{number}"
        job_dir = root / name
        try:
            job_dir.mkdir()
            return name, job_dir
        except FileExistsError:
            continue
    raise RuntimeError("Could not reserve a unique Illustrator流程图绘制 job directory")


def semantic_assets_resolved(manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    objects = manifest.get("objects")
    if not isinstance(objects, list):
        raise ValueError("scene manifest objects must be an array")
    manifest_root = manifest_path.parent
    for obj in objects:
        if not isinstance(obj, dict) or str(obj.get("type") or "").lower() not in SEMANTIC_TYPES:
            continue
        asset_value = obj.get("asset_svg")
        source = obj.get("source")
        provider = source.get("provider") if isinstance(source, dict) else source
        status = str(obj.get("status") or "").lower()
        if not asset_value or str(provider or "").lower() != "supersvg":
            return False
        asset_path = Path(str(asset_value))
        if not asset_path.is_absolute():
            asset_path = manifest_root / asset_path
        if not asset_path.is_file() or obj.get("vector_valid") is not True:
            return False
        if status not in {"accepted", "completed", "pass", "passed", "success"}:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-image", required=True, type=Path)
    parser.add_argument("--scene-manifest", required=True, type=Path)
    parser.add_argument("--text-manifest", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--supersvg-remote-root", default="services/supersvg-eval")
    parser.add_argument("--supersvg-gpu-index", type=int, default=1)
    parser.add_argument("--supersvg-rows", type=int, default=1)
    parser.add_argument("--supersvg-cols", type=int, default=1)
    parser.add_argument("--supersvg-overlap", type=int, default=64)
    parser.add_argument("--supersvg-path-num", type=int, default=1600)
    parser.add_argument("--supersvg-optimize-iter", type=int, default=14)
    parser.add_argument("--supersvg-refine-batch-size", type=int, default=8)
    parser.add_argument("--supersvg-timeout", type=int, default=7200)
    parser.add_argument("--per-asset", action="store_true", help="Reload SuperSVG once per complex asset instead of one batch load")
    parser.add_argument("--force-vectorize-assets", action="store_true")
    parser.add_argument("--sam3-foreground-clips", action="store_true")
    parser.add_argument("--sam3-remote-port", type=int, default=8765)
    parser.add_argument("--placement", default="center", choices=[
        "center", "top-center", "left-center", "bottom-center",
        "bottom-right", "top-right", "bottom-left", "top-left",
    ])
    parser.add_argument("--max-width-fraction", type=float, default=0.72)
    parser.add_argument("--max-height-fraction", type=float, default=0.78)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--min-batch-size", type=int, default=20)
    parser.add_argument("--max-batch-size", type=int, default=50)
    parser.add_argument("--checkpoint-batches", type=int, default=10)
    parser.add_argument("--checkpoint-seconds", type=int, default=30)
    parser.add_argument("--no-illustrator", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.supersvg_path_num < 1000:
        parser.error("quality mode requires --supersvg-path-num >= 1000")
    if args.supersvg_optimize_iter < 10:
        parser.error("quality mode requires --supersvg-optimize-iter >= 10")
    if args.supersvg_rows < 1 or args.supersvg_cols < 1 or args.supersvg_overlap < 0:
        parser.error("invalid SuperSVG tiling settings")

    input_path = args.input_image.resolve(strict=True)
    scene_input = args.scene_manifest.resolve(strict=True)
    text_manifest = args.text_manifest.resolve(strict=True)
    output_root = args.output_root.resolve()
    base_name, job_dir = reserve_job_directory(output_root)
    internal_dir = job_dir / ".illustrator-flowchart-internal"
    cache_dir = internal_dir / "live-cache"
    asset_dir = job_dir / "assets"
    resolved_scene = job_dir / f"{base_name}-scene-resolved.json"
    segmented_scene = job_dir / f"{base_name}-scene-segmented.json"
    raw_svg = job_dir / f"{base_name}-hybrid-base.svg"
    master_svg = job_dir / f"{base_name}.svg"
    output_ai = job_dir / f"{base_name}.ai"
    output_png = job_dir / f"{base_name}.png"
    internal_dir.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent

    run_checked([
        sys.executable, str(scripts / "validate_scene_manifest.py"),
        "--manifest", str(scene_input), "--allow-unresolved-assets",
    ])

    if args.force_vectorize_assets or not semantic_assets_resolved(scene_input):
        vector_command = [
            sys.executable, str(scripts / "vectorize_scene_assets.py"),
            "--input-image", str(input_path),
            "--scene-manifest", str(scene_input),
            "--output-manifest", str(resolved_scene),
            "--asset-dir", str(asset_dir),
            "--ssh-target", args.ssh_target,
            "--remote-root", args.supersvg_remote_root,
            "--gpu-index", str(args.supersvg_gpu_index),
            "--rows", str(args.supersvg_rows),
            "--cols", str(args.supersvg_cols),
            "--overlap", str(args.supersvg_overlap),
            "--path-num", str(args.supersvg_path_num),
            "--optimize-iter", str(args.supersvg_optimize_iter),
            "--refine-batch-size", str(args.supersvg_refine_batch_size),
            "--timeout", str(args.supersvg_timeout),
        ]
        if args.per_asset:
            vector_command.append("--per-asset")
        run_checked(vector_command, timeout=args.supersvg_timeout + 1200)
        active_scene = resolved_scene
    else:
        run_checked([
            sys.executable, str(scripts / "validate_scene_manifest.py"),
            "--manifest", str(scene_input),
        ])
        active_scene = scene_input

    if args.sam3_foreground_clips:
        run_checked([
            sys.executable, str(scripts / "segment_scene_assets_sam3.py"),
            "--scene-manifest", str(active_scene),
            "--output-manifest", str(segmented_scene),
            "--mask-dir", str(job_dir / "sam3-masks"),
            "--ssh-target", args.ssh_target,
            "--remote-port", str(args.sam3_remote_port),
        ], timeout=3600)
        active_scene = segmented_scene

    run_checked([sys.executable, str(scripts / "validate_scene_manifest.py"), "--manifest", str(active_scene)])
    run_checked([
        sys.executable, str(scripts / "build_hybrid_master.py"),
        "--scene-manifest", str(active_scene),
        "--output-svg", str(raw_svg),
    ])
    run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(raw_svg)])
    run_checked([
        sys.executable, str(scripts / "merge_live_text.py"),
        "--input-svg", str(raw_svg),
        "--text-manifest", str(text_manifest),
        "--output-svg", str(master_svg),
    ])
    run_checked([sys.executable, str(scripts / "validate_vector_svg.py"), "--svg", str(master_svg)])

    runner_command = [
        sys.executable, str(scripts / "run_illustrator_flowchart.py"),
        "--input-svg", str(master_svg),
        "--work-dir", str(cache_dir),
        "--output-ai", str(output_ai),
        "--output-png", str(output_png),
        "--job-id", base_name,
        "--placement", args.placement,
        "--max-width-fraction", str(args.max_width_fraction),
        "--max-height-fraction", str(args.max_height_fraction),
        "--delay-ms", str(args.delay_ms),
        "--min-batch-size", str(args.min_batch_size),
        "--max-batch-size", str(args.max_batch_size),
        "--checkpoint-batches", str(args.checkpoint_batches),
        "--checkpoint-seconds", str(args.checkpoint_seconds),
    ]
    system = platform.system().lower()
    illustrator_enabled = not args.no_illustrator and not args.dry_run and system in {"windows", "darwin"}
    if not illustrator_enabled:
        runner_command.append("--no-illustrator")
    if args.dry_run:
        runner_command.append("--dry-run")
    runner_output = run_checked(runner_command)
    render_report = None
    if illustrator_enabled:
        render_report_path = internal_dir / "render-equivalence.json"
        render_report = run_checked([
            sys.executable, str(scripts / "verify_render_equivalence.py"),
            "--source-svg", str(master_svg),
            "--candidate-png", str(output_png),
            "--report", str(render_report_path),
        ])

    result: dict[str, Any] = {
        "ok": True,
        "platform": system,
        "provider": "supersvg",
        "pipeline": "hybrid-object-routing",
        "mode": "illustrator" if illustrator_enabled else "svg-only",
        "base_name": base_name,
        "job_dir": str(job_dir),
        "scene_manifest": str(active_scene),
        "asset_dir": str(asset_dir) if asset_dir.exists() else None,
        "vector_svg": str(raw_svg),
        "svg": str(master_svg),
        "cache_dir": str(cache_dir),
        "ai": str(output_ai) if illustrator_enabled else None,
        "png": str(output_png) if illustrator_enabled else None,
        "runner": runner_output.splitlines()[-1] if runner_output else None,
        "render_qa": render_report.splitlines()[-1] if render_report else None,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ILLUSTRATOR_FLOWCHART_PIPELINE_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
