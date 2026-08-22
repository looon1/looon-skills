#!/usr/bin/env python3
"""Validate the content contract for a panel-complete journal-club workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CLAIM_FIELDS = {
    "question",
    "design",
    "read_order",
    "observation",
    "author_inference",
    "presenter_explanation",
    "presenter_boundary",
    "next_link",
    "source_lineage",
}


def nonempty(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()

    path = Path(args.contract).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    warnings: list[str] = []

    mode = data.get("coverage_mode")
    if mode not in {"selective", "full_main_figures", "all_figures"}:
        errors.append("coverage_mode must be selective, full_main_figures, or all_figures")

    phase = data.get("phase", "pre_authoring")
    if phase not in {"dry_run", "pre_authoring"}:
        errors.append("phase must be dry_run or pre_authoring")

    sections = {item.get("id") for item in data.get("result_sections", []) if item.get("id")}
    if not sections:
        errors.append("result_sections is empty")

    expected: set[str] = set()
    produced: dict[str, dict] = {}
    for figure in data.get("figures", []):
        figure_id = figure.get("figure_id")
        if not figure_id:
            errors.append("figure without figure_id")
            continue
        labels = figure.get("expected_labels", [])
        if len(labels) != len(set(labels)):
            errors.append(f"{figure_id}: duplicate expected_labels")
        for label in labels:
            expected.add(f"{figure_id}{label}")
        for panel in figure.get("panels", []):
            ref = f"{figure_id}{panel.get('label', '')}"
            if ref in produced:
                errors.append(f"duplicate panel record: {ref}")
            produced[ref] = panel

    if mode in {"full_main_figures", "all_figures"}:
        missing = sorted(expected - set(produced))
        extra = sorted(set(produced) - expected)
        if missing:
            errors.append("missing expected panels: " + ", ".join(missing))
        if extra:
            errors.append("unexpected panel records: " + ", ".join(extra))

    exceptions = {item.get("panel_ref") for item in data.get("exceptions", [])}
    accepted_count = 0
    for ref in sorted(expected):
        panel = produced.get(ref)
        if panel is None:
            continue
        status = panel.get("status")
        if status not in {"accepted", "needs_review", "exception"}:
            errors.append(f"{ref}: invalid status {status!r}")
        if status == "accepted":
            accepted_count += 1
        if phase == "pre_authoring" and status == "needs_review":
            errors.append(f"{ref}: crop still needs review before authoring")
        if status == "exception" and ref not in exceptions:
            errors.append(f"{ref}: exception has no exceptions[] record")
        section_id = panel.get("result_section_id")
        if section_id not in sections:
            errors.append(f"{ref}: unknown or missing result_section_id")
        if not panel.get("claim_id"):
            errors.append(f"{ref}: missing claim_id")

    claims = {item.get("id"): item for item in data.get("claims", []) if item.get("id")}
    for ref in sorted(expected):
        panel = produced.get(ref)
        if not panel:
            continue
        claim = claims.get(panel.get("claim_id"))
        if not claim:
            errors.append(f"{ref}: claim record not found")
            continue
        missing_fields = sorted(field for field in REQUIRED_CLAIM_FIELDS if not nonempty(claim.get(field)))
        if missing_fields:
            errors.append(f"{ref}: incomplete claim fields: {', '.join(missing_fields)}")
        if ref not in claim.get("panel_refs", []):
            errors.append(f"{ref}: claim does not list panel_ref")

    slide_panel_refs: set[str] = set()
    slides = data.get("slides", [])
    for slide in slides:
        slide_id = slide.get("slide_id", "<unknown>")
        if slide.get("result_section_id") not in sections:
            errors.append(f"{slide_id}: missing or unknown Results section")
        if not nonempty(slide.get("assertion_title_zh")):
            errors.append(f"{slide_id}: missing assertion_title_zh")
        slide_panel_refs.update(slide.get("panel_refs", []))

    if mode in {"full_main_figures", "all_figures"}:
        unmapped = sorted(expected - slide_panel_refs - exceptions)
        if unmapped:
            errors.append("panels absent from slide plan: " + ", ".join(unmapped))

    notes = data.get("speaker_notes", [])
    note_ids = {item.get("slide_id") for item in notes if item.get("slide_id")}
    if phase == "pre_authoring":
        missing_notes = sorted(
            slide.get("slide_id") for slide in slides
            if slide.get("substantive", True) and slide.get("slide_id") not in note_ids
        )
        if missing_notes:
            errors.append("substantive slides without notes: " + ", ".join(missing_notes))
    elif len(notes) < 3:
        warnings.append("dry_run has fewer than three speaker-note samples")

    result = {
        "status": "pass" if not errors else "fail",
        "coverage_mode": mode,
        "phase": phase,
        "expected_panel_count": len(expected),
        "panel_record_count": len(produced),
        "accepted_panel_count": accepted_count,
        "slide_mapped_panel_count": len(expected & slide_panel_refs),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
