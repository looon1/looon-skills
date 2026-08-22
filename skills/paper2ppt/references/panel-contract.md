# Panel manifest contract

Create one manifest per source Figure. Use pixel coordinates relative to the frozen `source_image` unless `bbox_space` is `normalized`.

## Minimal schema

```json
{
  "schema_version": "1.0",
  "figure_id": "fig2",
  "source_image": "/absolute/path/source.png",
  "source_sha256": "...",
  "source_page": 4,
  "source_figure": "Figure 2",
  "caption": "Full source caption",
  "bbox_space": "pixels",
  "panels": [
    {
      "id": "fig2_top",
      "label": null,
      "kind": "semantic_group",
      "bbox": [92, 8, 1128, 692],
      "margin_px": 8,
      "caption_segment": "Results for the original N=206 subset",
      "evidence": ["visual_group", "caption_cohort:N=206"],
      "detectors": [{"name": "codex_visual", "confidence": 0.91}],
      "shared_assets": [],
      "parent_id": null,
      "status": "accepted",
      "reviewer_note": "Cohort label, ROC curves, KM curves, and legends retained."
    }
  ]
}
```

## Coordinate rules

- Pixel bbox uses `[left, top, right, bottom]` with an exclusive right/bottom edge.
- Normalized bbox uses the same order with values in `[0,1]`.
- Keep the source dimensions and checksum stable after proposing boxes.
- Use margin only to preserve context; never use it to absorb a neighboring panel silently.

## Kinds

- `labeled_panel`: explicit printed panel label.
- `semantic_group`: coherent unlabeled result/method/cohort region.
- `shared_asset`: legend, scale, color bar, shared title, or shared axis.
- `inset`: nested region with `parent_id`.

## Status gate

`accepted` requires:

- valid bbox inside the frozen image;
- nonempty evidence and detector ledger;
- caption segment or an explicit explanation that the Figure has no panel-resolved caption;
- no known clipped axis, legend, panel label, scale bar, statistical annotation, or scientific subject;
- a reviewer note stating what was checked.

Use `needs_review` for ambiguous borders, shared assets, incomplete captions, or one-source proposals. Use `rejected` for wrong, duplicate, blank, text-only, or scientifically incomplete proposals.

## Manifest-to-slide lineage

Record in `asset_manifest.md`:

```text
slide | claim | figure_id | panel_id | source_page | crop_status | source
```

Do not insert a panel into the final deck unless this row exists.
