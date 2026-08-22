#!/usr/bin/env python3
"""Validate and normalize a panel-aware Paper2PPT style contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_BRANDING = {"none", "auto", "university", "lab"}


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True, help="Path to style_spec.json")
    parser.add_argument("--registry", help="Optional style-presets.json override")
    parser.add_argument("--output", help="Write normalized contract to this path")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    registry_path = (
        Path(args.registry).expanduser().resolve()
        if args.registry
        else script_dir.parent / "assets" / "style-presets.json"
    )
    spec_path = Path(args.spec).expanduser().resolve()
    registry = load_json(registry_path)
    spec = load_json(spec_path)

    if registry.get("schema_version") != "1.0":
        raise ValueError("registry schema_version must be 1.0")
    if spec.get("schema_version") != "1.0":
        raise ValueError("spec schema_version must be 1.0")

    presets = registry.get("presets")
    if not isinstance(presets, dict) or not presets:
        raise ValueError("registry presets must be a nonempty object")

    style_id = spec.get("style_id")
    if style_id not in presets:
        raise ValueError(f"unknown style_id: {style_id!r}; allowed: {sorted(presets)}")
    preset = presets[style_id]

    density = spec.get("density") or preset["default_density"]
    if density not in preset["allowed_density"]:
        raise ValueError(
            f"{style_id}: density {density!r} not in {preset['allowed_density']}"
        )

    figure_layout = spec.get("figure_layout") or preset["default_figure_layout"]
    if figure_layout not in preset["allowed_figure_layout"]:
        raise ValueError(
            f"{style_id}: figure_layout {figure_layout!r} not in "
            f"{preset['allowed_figure_layout']}"
        )

    branding = spec.get("branding", "auto")
    if branding not in ALLOWED_BRANDING:
        raise ValueError(f"branding must be one of {sorted(ALLOWED_BRANDING)}")

    accent_variant = spec.get("accent_variant")
    variants = preset.get("accent_variants")
    if accent_variant is not None:
        if not variants or accent_variant not in variants:
            allowed = sorted(variants) if variants else []
            raise ValueError(f"{style_id}: invalid accent_variant; allowed: {allowed}")
    elif preset.get("default_accent_variant"):
        accent_variant = preset["default_accent_variant"]

    if "palette" in spec and spec["palette"] != preset["palette"]:
        raise ValueError("palette overrides are not allowed; select a preset/variant")

    normalized = dict(spec)
    normalized.update(
        {
            "schema_version": "1.0",
            "style_id": style_id,
            "style_label_zh": preset["label_zh"],
            "density": density,
            "figure_layout": figure_layout,
            "branding": branding,
            "palette": preset["palette"],
            "allowed_layouts": preset["layouts"],
        }
    )
    if accent_variant is not None:
        normalized["accent_variant"] = accent_variant
        normalized["accent_color"] = variants[accent_variant]

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(normalized, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
