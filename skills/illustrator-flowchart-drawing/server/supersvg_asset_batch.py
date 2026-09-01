#!/usr/bin/env python3
"""Vectorize a directory of complex-asset crops with one SuperSVG model load."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from supersvg_tiled import prepare_tiles, stitch


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
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

    inputs = [path for path in sorted(args.input_dir.resolve().iterdir()) if path.suffix.lower() in IMAGE_EXTENSIONS]
    if not inputs:
        raise FileNotFoundError(f"No asset crops found in {args.input_dir}")
    output_dir = args.output_dir.resolve()
    work_dir = output_dir / ".batch-work"
    common_tiles = work_dir / "tiles"
    common_vectors = work_dir / "vectors"
    common_tiles.mkdir(parents=True, exist_ok=True)
    common_vectors.mkdir(parents=True, exist_ok=True)
    records = []

    for image_path in inputs:
        asset_work = work_dir / image_path.stem
        prepared_dir = asset_work / "prepared"
        manifest = prepare_tiles(image_path, prepared_dir, args.rows, args.cols, args.overlap)
        tile_records = []
        for tile in manifest["tiles"]:
            tile_name = tile["name"]
            batch_name = f"asset-{image_path.stem}--{tile_name}"
            shutil.copy2(prepared_dir / f"{tile_name}.png", common_tiles / f"{batch_name}.png")
            tile_records.append({"tile_name": tile_name, "batch_name": batch_name})
        records.append({
            "id": image_path.stem,
            "tiles": tile_records,
            "manifest": manifest,
            "asset_work": str(asset_work),
        })

    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "inference.py"),
        "--input_path", str(common_tiles),
        "--output_dir", str(common_vectors),
        "--device", args.device,
        "--path_num", str(args.path_num),
        "--optimize_iter", str(args.optimize_iter),
        "--refine_batch_size", str(args.refine_batch_size),
    ]
    subprocess.run(command, check=True, cwd=Path(__file__).resolve().parent)

    output_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        asset_work = Path(record["asset_work"])
        vector_dir = asset_work / "vector"
        vector_dir.mkdir(parents=True, exist_ok=True)
        for tile_record in record["tiles"]:
            shutil.copy2(
                common_vectors / f"{tile_record['batch_name']}.svg",
                vector_dir / f"{tile_record['tile_name']}.svg",
            )
        stitch(record["manifest"], vector_dir, output_dir / f"{record['id']}.svg")

    report = {
        "ok": True,
        "asset_count": len(records),
        "rows": args.rows,
        "cols": args.cols,
        "overlap": args.overlap,
        "path_num_per_asset": args.path_num,
        "optimize_iter": args.optimize_iter,
        "refine_batch_size": args.refine_batch_size,
        "outputs": [str(output_dir / f"{record['id']}.svg") for record in records],
    }
    (output_dir / "batch-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
