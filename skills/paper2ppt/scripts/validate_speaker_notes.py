#!/usr/bin/env python3
"""Validate panel-aware speaker notes before PPTX authoring."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).strip("。；;,.，")


def load_slides(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("slides"), list):
        return data["slides"]
    raise ValueError(f"{path}: expected a list or an object with slides[]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notes", required=True)
    parser.add_argument("--plan", required=True)
    args = parser.parse_args()

    notes_path = Path(args.notes).expanduser().resolve()
    plan_path = Path(args.plan).expanduser().resolve()
    notes = load_slides(notes_path)
    plan = load_slides(plan_path)

    errors: list[str] = []
    warnings: list[str] = []
    note_by_id = {item.get("slide_id"): item for item in notes if item.get("slide_id")}
    scripts: defaultdict[str, list[str]] = defaultdict(list)
    banned = ("重磅发现", "惊人机制", "关键突破", "深入揭示", "非常重要的故事")

    for item in plan:
        slide_id = item.get("slide_id")
        if not slide_id:
            continue
        substantive = item.get("substantive", bool(item.get("panel_refs")))
        if not substantive:
            continue
        note = note_by_id.get(slide_id)
        if note is None:
            errors.append(f"{slide_id}: substantive slide has no speaker note")
            continue
        script = str(note.get("script_zh", "")).strip()
        if not script:
            errors.append(f"{slide_id}: script_zh is empty")
            continue
        sources = note.get("sources") or []
        if not sources:
            errors.append(f"{slide_id}: sources is empty")
        transition = str(note.get("transition", "")).strip()
        if not transition:
            errors.append(f"{slide_id}: transition is empty")
        expected_panels = set(item.get("panel_refs") or [])
        actual_panels = set(note.get("covered_panels") or [])
        if expected_panels != actual_panels:
            errors.append(
                f"{slide_id}: covered_panels {sorted(actual_panels)} does not match panel_refs {sorted(expected_panels)}"
            )
        normalized = normalize(script)
        scripts[normalized].append(slide_id)
        if any(term in script for term in banned):
            errors.append(f"{slide_id}: promotional or AI-style wording detected")
        length = len(normalized)
        if length < 80:
            warnings.append(f"{slide_id}: short evidence script ({length} Chinese/nonspace characters)")
        if length > 520 and not note.get("length_exception"):
            errors.append(f"{slide_id}: evidence script exceeds 520 characters without length_exception")

    for script, slide_ids in scripts.items():
        if script and len(slide_ids) > 1:
            errors.append(f"duplicated normalized script across slides: {', '.join(slide_ids)}")

    result = {
        "status": "pass" if not errors else "fail",
        "notes": len(notes),
        "planned_slides": len(plan),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
