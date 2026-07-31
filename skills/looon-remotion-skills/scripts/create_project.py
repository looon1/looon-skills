#!/usr/bin/env python3
"""Create a configured Remotion project from the bundled Looon template."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--background-image", type=Path)
    parser.add_argument(
        "--background-mode",
        choices=("grid", "image", "solid"),
        default=None,
    )
    parser.add_argument("--background-color", default="#fffaf0")
    parser.add_argument("--accent-color", default="#f6bc35")
    parser.add_argument("--ink-color", default="#17140f")
    parser.add_argument("--paper-color", default="#fffaf0")
    parser.add_argument(
        "--background-motion",
        choices=("left-to-right", "right-to-left", "none"),
        default="left-to-right",
    )
    parser.add_argument("--background-travel", type=float, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    skill_root = Path(__file__).resolve().parent.parent
    template = skill_root / "assets" / "template"
    output = args.output.expanduser().resolve()

    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing destination: {output}")
    if args.background_image and not args.background_image.expanduser().is_file():
        raise SystemExit(f"Background image does not exist: {args.background_image}")

    shutil.copytree(template, output)

    theme_path = output / "src" / "theme.json"
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    theme["background"]["color"] = args.background_color
    theme["palette"]["accent"] = args.accent_color
    theme["palette"]["ink"] = args.ink_color
    theme["palette"]["paper"] = args.paper_color
    theme["background"]["motion"]["enabled"] = args.background_motion != "none"
    if args.background_motion != "none":
        theme["background"]["motion"]["direction"] = args.background_motion
    theme["background"]["motion"]["distance"] = args.background_travel

    if args.background_image:
        source = args.background_image.expanduser().resolve()
        destination_name = f"background{source.suffix.lower() or '.png'}"
        shutil.copy2(source, output / "public" / destination_name)
        theme["background"]["mode"] = "image"
        theme["background"]["image"] = destination_name
    else:
        theme["background"]["mode"] = args.background_mode or "grid"
        theme["background"]["image"] = None

    theme_path.write_text(
        json.dumps(theme, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Created: {output}")
    print(f"Theme: {theme_path}")
    print("Next: npm install && npm run render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
