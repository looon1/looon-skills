#!/usr/bin/env python3
"""Offline integration test for object routing, hybrid composition, and cache schema 5."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


def main() -> int:
    scripts = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="illustrator-flowchart-self-test-") as temporary:
        root = Path(temporary)
        image = root / "reference.png"
        Image.new("RGB", (400, 300), "white").save(image)
        asset = root / "complex.svg"
        asset.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path id="complex-shape" d="M5 10 L90 5 L98 85 L15 95 Z" fill="#9f6678"/>'
            '</svg>',
            encoding="utf-8",
        )
        scene = root / "scene.json"
        scene.write_text(json.dumps({
            "schema_version": "1.0",
            "canvas_size": {"width": 400, "height": 300},
            "objects": [
                {
                    "id": "background", "type": "background", "draw_order": 1,
                    "coordinate_space": "absolute", "bbox": {"x": 10, "y": 10, "width": 380, "height": 280},
                    "gradient": {"type": "linear", "x1": "0%", "y1": "0%", "x2": "100%", "y2": "100%", "stops": [
                        {"offset": "0%", "color": "#edf5f8"}, {"offset": "100%", "color": "#d8e8ef"},
                    ]},
                },
                {
                    "id": "dashed-line", "type": "line", "draw_order": 2, "coordinate_space": "absolute",
                    "x1": 30, "y1": 85, "x2": 180, "y2": 85,
                    "style": {"stroke": "#536274", "stroke_width": 4, "stroke_dasharray": "12 7"},
                },
                {
                    "id": "native-arrow", "type": "arrow", "draw_order": 3, "coordinate_space": "absolute",
                    "x1": 45, "y1": 150, "x2": 180, "y2": 150,
                },
                {
                    "id": "complex-asset", "type": "semantic_asset", "draw_order": 4,
                    "coordinate_space": "absolute", "bbox": {"x": 225, "y": 45, "width": 145, "height": 190},
                    "asset_svg": str(asset), "source": {"provider": "supersvg", "scope": "complex-asset-crop"},
                    "status": "accepted", "vector_valid": True,
                    "clip_contours": [
                        [[0.0, 0.0], [0.64, 0.0], [0.58, 0.52], [0.0, 0.55]],
                        [[0.35, 0.58], [1.0, 0.48], [1.0, 1.0], [0.28, 1.0]],
                    ],
                },
            ],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        text = root / "text.json"
        text.write_text(json.dumps({
            "schema_version": "1.0",
            "text_elements": [{
                "id": "live-title", "content": "Live text", "x": 0.08, "y": 0.18,
                "coordinate_space": "normalized", "font_family": "Arial", "font_size": 24,
                "font_weight": "bold", "fill": "#20252b", "paint_order": 5,
            }],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        output = root / "output"
        result = subprocess.run([
            sys.executable, str(scripts / "run_from_image.py"),
            "--input-image", str(image), "--scene-manifest", str(scene),
            "--text-manifest", str(text), "--output-root", str(output), "--no-illustrator",
        ], text=True, capture_output=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        cache_path = Path(payload["cache_dir"]) / "geometry-cache.json"
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        assert cache["schema_version"] == 5
        assert any(atom["kind"] == "text" for atom in cache["atoms"])
        assert any(part.get("fillGradient") for atom in cache["atoms"] for part in atom.get("paintParts", []))
        assert any(part.get("strokeDashes") for atom in cache["atoms"] for part in atom.get("paintParts", []))
        assert any(len((atom.get("clip") or {}).get("subpaths", [])) > 1 for atom in cache["atoms"])
        master = Path(payload["svg"])
        assert "<image" not in master.read_text(encoding="utf-8")
        print(json.dumps({
            "ok": True,
            "pipeline": payload["pipeline"],
            "provider": payload["provider"],
            "atoms": cache["total_atoms"],
            "batches": len(cache["batches"]),
            "raster_nodes": 0,
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
