---
name: paper2ppt
description: Turn a scientific paper or PDF into a source-grounded Chinese journal-club, lab-meeting, thesis-seminar, or paper-sharing PPTX with auditable Figure extraction, panel-level crops, Results-section argument mapping, complete-main-Figure coverage when requested, and selectable academic visual systems. Use when the user asks for paper PPT, paper2ppt, journal club slides, 文献精讲, 逐图讲解, 主图全部panel, 论文汇报PPT, 拆分论文Figure/panel, 蓝色简约/极简/Nature风/绿色科研PPT, or a presentation that must keep panel labels, axes, legends, scale bars, cohorts, captions, slide claims, and oral notes correctly aligned. Supports rule-only dry runs, PDF-native extraction, OCR/layout-assisted panel proposals, visual review, semantic panel groups, manifest-driven cropping, ten locked style presets, and optional downstream Crafter reconstruction for diagram-like panels.
---

# Paper2PPT

Build the evidence chain before building slides. Never let slide layout determine a scientific crop.

## Required resources

- Read [references/panel-contract.md](references/panel-contract.md) before extracting or accepting any panel.
- Read [references/detector-routing.md](references/detector-routing.md) before selecting PDF, OCR, VLM, FigEx, SAM, or manual routes.
- Read [references/deck-workflow.md](references/deck-workflow.md) before planning or creating the PPTX.
- Read [references/paper-interpretation.md](references/paper-interpretation.md) before writing slide claims, Figure explanations, or speaker notes.
- Read [references/reference-language-notes.md](references/reference-language-notes.md) when the user supplies a PPTX as a language, density, or speaker-note reference, or requests formal academic oral-report wording.
- Read [references/precision-journal-club.md](references/precision-journal-club.md) when the user requests 精讲, 逐图讲解, every/main Figure panel, or Results-heading-led structure.
- Read [references/dry-run-evaluation.md](references/dry-run-evaluation.md) when the user asks to define rules, test the Skill, or evaluate it without producing a PPTX.
- Read [references/style-system.md](references/style-system.md) before choosing a visual style or writing a deck plan.
- Read [references/nature-green-journal-club.md](references/nature-green-journal-club.md) when the user asks for the green version, selects `nature_green_journal_club`, or supplies the previously approved green journal-club reference.
- Read [references/evaluation.md](references/evaluation.md) before final delivery.

For a local PDF, also use the installed PDF skill. For a real `.pptx`, use the installed Presentations skill and obey its runtime, rendering, notes, and overlap rules. Use `crafter-editable-image` only under the Crafter boundary below.

## Outputs

Create a task-scoped output tree:

```text
output/
├── source/
├── deck_brief.json
├── style_spec.json
├── paper_digest.json
├── argument_map.json
├── figure_claims.json
├── coverage_contract.json
├── deck_plan.json
├── speaker_notes.json
├── figures/<figure-id>/
│   ├── source.png
│   ├── panel_manifest.json
│   ├── overlay_review.png
│   ├── contact_sheet.png
│   └── panels/*.png
├── asset_manifest.md
├── source_notes.txt
├── panel_qa.json
├── render/
├── qa_report.md
└── <paper>-journal-club.pptx
```

Do not copy copyrighted paper assets into the installed Skill. Keep them in the task output and confirm redistribution rights before publishing.

## Workflow

### 1. Freeze the source

Record the absolute PDF path or canonical article URL, title, DOI/PMID when available, byte size, page count, checksum, acquisition route, and access limitations. Prefer, in order:

1. publisher or repository full-resolution Figure asset;
2. an image/vector object extracted from the official PDF;
3. a high-DPI render of the exact Figure region;
4. a page screenshot only as a disclosed fallback.

Never substitute another paper, Figure, or low-resolution screenshot silently.

### 2. Classify the paper and reconstruct its argument

Classify as `discovery`, `methods`, `resource`, `clinical`, `materials`, or `review`. Follow [references/paper-interpretation.md](references/paper-interpretation.md) and create `paper_digest.json`, `argument_map.json`, and `figure_claims.json` before choosing slides. Build a terminology ledger and a claim-evidence table. Use the scientific argument, not manuscript section order, as the deck spine.

Choose `coverage_mode` before selecting evidence:

- `selective`: use only panels needed for the requested summary;
- `full_main_figures`: enumerate and map every labeled panel in every main-text Figure;
- `all_figures`: include main, Extended Data, and Supplementary Figures.

Treat 精讲, 逐图讲解, 主图全部 panel, and equivalent wording as `full_main_figures`. Do not silently downgrade it to `selective`. Follow [references/precision-journal-club.md](references/precision-journal-club.md) and create `coverage_contract.json`.

### 3. Lock the deck contract and visual system

Create `deck_brief.json`, `style_spec.json`, `deck_plan.json`, and `speaker_notes.json` before rendering. Follow [references/style-system.md](references/style-system.md). Keep paper type, audience, purpose, style, density, Figure treatment, and branding as separate axes.

Use `nature_green_journal_club` for the user's approved green journal-club baseline. Otherwise use `academic_blue_nav` by default for a dense Chinese biomedical group meeting unless the user provides a reference or another preset clearly fits better. Present style choices by their Chinese labels when the user asks to choose freely. Validate the chosen contract before authoring:

```bash
python scripts/validate_style_spec.py --spec /absolute/path/style_spec.json
```

Validate the oral-report contract before authoring:

```bash
python scripts/validate_speaker_notes.py \
  --notes /absolute/path/speaker_notes.json \
  --plan /absolute/path/deck_plan.json
```

Do not let a theme alter an accepted crop. Evidence geometry is frozen before slide layout.

### 4. Inventory Figures before splitting them

For every candidate Figure, record its Figure number, page, full caption, source bbox, source resolution, scientific role, expected panel labels, and whether it is needed. In `selective` mode, select only evidence that advances the presentation. In `full_main_figures` or `all_figures` mode, every in-scope panel must be accepted, marked `needs_review`, or listed as an explicit exception; omission is a failure. Do not split decorative or unused Figures unless they are explicitly in scope.

### 5. Produce panel proposals

Follow [references/detector-routing.md](references/detector-routing.md). Preserve every proposal source and confidence. A proposal may be:

- `labeled_panel`: explicit `a`, `b`, `c`, etc.;
- `semantic_group`: an unlabeled but scientifically coherent cohort, method block, or result block;
- `shared_asset`: legend, color bar, scale key, shared axis title, or annotation needed by multiple panels;
- `inset`: a nested visual whose parent relationship must be retained.

Use OCR as label/text evidence, not as the sole panel detector. Use SAM-style masks only to refine an already grounded visual object; do not equate arbitrary objects with panels.

### 6. Reconcile geometry with semantics

Match each proposed crop against panel labels, caption segments, reading order, plot/axis/legend continuity, cohort/condition/sample-size wording, shared assets, and inset relationships. Merge or expand proposals when a crop would separate a result from necessary context.

### 7. Gate and materialize panels

Create `panel_manifest.json` following [references/panel-contract.md](references/panel-contract.md). Mark every entry `accepted`, `needs_review`, or `rejected`.

Only materialize boxes with:

```bash
python scripts/materialize_panels.py \
  --manifest /absolute/path/panel_manifest.json \
  --output-dir /absolute/path/figure-output
```

`materialize_panels.py` requires Pillow. For Codex desktop document work, use the bundled workspace Python returned by the workspace-dependency loader; otherwise verify `python -c "import PIL"` before the batch. Report a missing runtime dependency as a test failure instead of silently skipping crop QA.

Inspect `overlay_review.png` and every crop at full size. The script validates and crops approved boxes; it does not discover panels and must never be reported as an AI detector.

### 8. Decide the asset representation

- Preserve microscopy, radiology, pathology, heatmaps, complex plots, and original quantitative results as high-resolution raster unless trustworthy source vectors or data are available.
- Recreate tables or charts only from explicit source values and verify every value.
- Use native PPT text for presentation annotations, not to overwrite or silently alter the paper.
- Route workflow diagrams, mechanism diagrams, and model architecture panels to Crafter only when editability materially helps.

### 9. Build the PPTX and oral notes

Follow [references/deck-workflow.md](references/deck-workflow.md). Build a real `.pptx`, add a source-grounded Chinese oral script and source block to every substantive slide, and keep visible Chinese copy concise. Every evidence-slide title must state the result or inference that the displayed evidence supports. Prefer one readable panel plus interpretation over a dense full Figure.

When a Figure is split across slides, write a distinct script for the panels visible on each slide. Never duplicate the full script from the preceding or following slide. Keep the chapter-level Results anchor stable while the assertion title and oral explanation remain panel-specific.

For `full_main_figures`, retain the exact Results subsection as the chapter hierarchy and use a panel-specific assertion as the slide title. When the approved reference uses dedicated Results dividers, do not add a redundant micro-anchor to every evidence slide. Panels may share a slide only when all remain readable and their combined role is explicit; split dense panels across additional slides, and allow the same local-conclusion title on adjacent continuation slides. Do not add visible labels such as `解释边界` or `证据边界` unless they exist in the approved reference. Run:

```bash
python scripts/validate_precision_contract.py --contract /absolute/path/coverage_contract.json
```

Do not author the PPTX while this validator reports an error.

Close a full-paper explanation with the source study-design Figure or a reconstructed end-to-end technical or evidence route as defined in [references/deck-workflow.md](references/deck-workflow.md). Keep this full technical-route recap in the final one or two slides after all Results evidence; do not place a duplicate route near the beginning unless the user explicitly asks for it. When both a reconstructed route and an author-supplied visual abstract exist, show the route first and the original visual abstract last. Do not substitute two generic limitations and conclusion lists for this recap.

Before locking an evidence layout, audit the accepted raster against its planned frame:

```bash
python scripts/audit_evidence_fill.py \
  --image /absolute/path/panel.png \
  --frame-width 824 --frame-height 472
```

Treat exit code `2` as a layout failure. Do not deliver a large evidence frame when the projected asset fill is below `0.45` or the projected scientific-content fill is below `0.35`. For a narrow compound panel, preserve the accepted panel as the source object and use disclosed zoom fragments in `L11_narrow_panel_zoom_strip`, or a locator view plus one to three readable zooms. Zoom fragments remain parts of the same panel and do not increase coverage counts. If safe internal boundaries cannot be established, pair the panel with directly linked evidence or reacquire a tighter source; do not stretch, crop away axes or legends, or add filler text and decoration.

### 10. Crafter boundary

For an accepted diagram-like panel, pass the frozen crop to `crafter-editable-image` in `existing-image` mode. Preserve Crafter's official Extraction → Processing → Composition sequence. Do not patch Crafter, preclassify before SAM3, or call a full-canvas raster editable.

Do not route data-bearing plots, medical images, microscopy, or heatmaps through generative cleaning merely to make them look editable. Keep scientific data pixels unchanged.

### 11. Validate and deliver

Apply [references/evaluation.md](references/evaluation.md). Render every slide and inspect it individually. A successful build requires traceable source → claim → Figure → panel → slide → spoken sentence lineage; a validated style contract; no clipped scientific context; correct panel-caption/cohort pairing; readable assets; no overlap/overflow; disclosed low-confidence crops; assertion titles supported by displayed evidence; and speaker-note sources.

If panel confidence is insufficient, deliver the Figure-level crop or pause for user confirmation. Never guess a scientific boundary.
