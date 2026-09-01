#!/usr/bin/env python3
"""Fail when an Illustrator PNG visibly diverges from the validated Master SVG."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


RMSE_RE = re.compile(r"\((?P<normalized>[0-9]*\.?[0-9]+(?:[eE][+-]?\d+)?)\)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-svg", required=True, type=Path)
    parser.add_argument("--candidate-png", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--reference-png", type=Path)
    parser.add_argument("--diff-png", type=Path)
    parser.add_argument("--max-normalized-rmse", type=float, default=0.055)
    parser.add_argument("--fallback-font", type=Path, default=Path("/System/Library/Fonts/Supplemental/Arial.ttf"))
    args = parser.parse_args()
    magick = shutil.which("magick")
    if not magick:
        raise RuntimeError("ImageMagick 'magick' is required for render-equivalence QA")

    source_svg = args.source_svg.resolve(strict=True)
    candidate_png = args.candidate_png.resolve(strict=True)
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    reference_png = (args.reference_png or report_path.with_name(report_path.stem + "-reference.png")).resolve()
    diff_png = (args.diff_png or report_path.with_name(report_path.stem + "-diff.png")).resolve()
    raw_reference = report_path.with_name(report_path.stem + "-reference-raw.png").resolve()
    normalized_candidate = report_path.with_name(report_path.stem + "-candidate-normalized.png").resolve()

    render_command = [magick, "-background", "white"]
    if args.fallback_font.exists():
        render_command.extend(["-font", str(args.fallback_font.resolve())])
    render_command.extend([str(source_svg), str(raw_reference)])
    render = subprocess.run(
        render_command,
        text=True, capture_output=True, timeout=600,
    )
    if render.returncode != 0:
        raise RuntimeError(render.stderr.strip() or "Could not render Master SVG for QA")
    normalize_suffix = [
        "-background", "white", "-alpha", "remove", "-alpha", "off",
        "-fuzz", "2%", "-trim", "+repage", "-resize", "1000x1000",
        "-gravity", "center", "-background", "white", "-extent", "1000x1000",
    ]
    for source, destination in ((raw_reference, reference_png), (candidate_png, normalized_candidate)):
        normalized = subprocess.run(
            [magick, str(source), *normalize_suffix, str(destination)],
            text=True, capture_output=True, timeout=180,
        )
        if normalized.returncode != 0:
            raise RuntimeError(normalized.stderr.strip() or f"Could not normalize {source.name} for QA")
    compare = subprocess.run(
        [magick, "compare", "-metric", "RMSE", str(reference_png), str(normalized_candidate), str(diff_png)],
        text=True, capture_output=True, timeout=180,
    )
    metric_text = (compare.stderr or compare.stdout).strip()
    match = RMSE_RE.search(metric_text)
    if not match:
        raise RuntimeError(f"Could not parse ImageMagick RMSE: {metric_text}")
    normalized_rmse = float(match.group("normalized"))
    passed = normalized_rmse <= args.max_normalized_rmse
    report = {
        "schema_version": "1.0",
        "status": "PASS" if passed else "FAIL",
        "source_svg": str(source_svg),
        "candidate_png": str(candidate_png),
        "candidate_normalized_png": str(normalized_candidate),
        "reference_png": str(reference_png),
        "diff_png": str(diff_png),
        "normalized_rmse": normalized_rmse,
        "max_normalized_rmse": args.max_normalized_rmse,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not passed:
        raise RuntimeError(
            f"RENDER_MISMATCH|normalized_rmse={normalized_rmse:.6f}|limit={args.max_normalized_rmse:.6f}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RENDER_EQUIVALENCE_ERROR|{exc}")
        raise SystemExit(1)
