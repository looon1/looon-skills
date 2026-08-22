# Selectable academic visual system

Choose a preset after the scientific argument and evidence map exist. Style controls composition, typography, color, and visual rhythm; it never changes a Figure or panel boundary.

## Contract axes

Create `style_spec.json` with these independent axes:

```json
{
  "schema_version": "1.0",
  "style_id": "academic_blue_nav",
  "density": "compact",
  "figure_layout": "panel_first",
  "branding": "auto",
  "paper_type": "methods",
  "audience": "biomedical lab meeting",
  "purpose": "Chinese journal club"
}
```

- `style_id`: visual system, not merely a color.
- `density`: `compact`, `standard`, or `airy` when allowed by the preset.
- `figure_layout`: `panel_first`, `mixed`, or `figure_level` when allowed by the preset.
- `branding`: `none`, `auto`, `university`, or `lab`.
- `paper_type`, `audience`, and `purpose`: routing evidence; they do not override source facts.

Validate the file with `scripts/validate_style_spec.py`. The registry is `assets/style-presets.json`.

## Preset routing

### `nature_green_journal_club` — Nature 墨绿·组会精讲版

User-validated baseline for full-paper biomedical journal clubs. Use prominent Results dividers, a white canvas with restrained forest-green rules, large objective assertion titles, 60–75% evidence area, and a pale-green result strip. Prefer `compact + panel_first`. Read [nature-green-journal-club.md](nature-green-journal-club.md) before rendering this preset.

This is a complete composition preset, not a palette swap. Do not add visible production labels, side rails, decorative card grids, or a workflow Figure before Results. If both a reconstructed technical route and the paper's visual abstract exist, place the route recap first and the source visual abstract on the final slide.

### `academic_blue_nav` — 科研蓝·高密度导航

Default for Chinese biomedical journal clubs and panel-heavy papers. Use a white canvas, navy top section rail, one active section marker, thin rectangular rules, large Figure area, and a stable takeaway strip. Prefer `compact + panel_first`.

Do not turn every region into a rounded card. The navigation rail is structural; the slide must still read as a flat scientific page.

### `journal_white` — 期刊白·极简图证

Use for one decisive experiment or mechanism per slide. Use high whitespace, sparse rules, a strong action title, one dominant panel, and a short evidence interpretation. Prefer `standard + panel_first`.

### `editorial_nature` — Nature 编辑部·杂志风

Use for high-level paper introductions, synthesis, and cross-disciplinary talks. Combine restrained serif display titles with sans-serif scientific labels, pale blue-gray fields, editorial captions, and asymmetric but grid-bound composition. Prefer `standard` or `airy`.

Do not use generated decorative images in place of scientific evidence.

### `clinical_blue` — 医学院·蓝色简约

Use for formal hospital, medical-school, proposal, mid-term, or defense contexts. Use institutional blue, a conventional title hierarchy, moderate density, optional logo, and consistent headers/footers. Prefer `standard + mixed`.

### `mono_accent` — 单色高级·紫/青/酒红

Use when the user wants personality without losing academic restraint. Keep a white canvas and one approved accent variant across the deck. Default to purple; approved variants are defined in the registry. Prefer `standard`.

### `dark_imaging` — 深色影像·显微优先

Use when most key evidence is dark-field fluorescence, radiology, pathology, spatial imaging, or black-background plots. Preserve source black levels, use cool cyan/blue accents, and keep annotations outside data pixels. Prefer `standard + panel_first`.

Do not auto-select this preset from one isolated dark panel. Use it when dark evidence dominates the core slide sequence.

### `warm_beige_review` — 暖米白·综述杂志版

Use for review talks, conceptual synthesis, and papers dominated by diagrams or clinical framing. Use warm off-white fields, brown-gray typography, restrained terracotta accents, and editorial captions. Prefer `standard` or `airy`; do not use it to reduce quantitative Figure area.

### `tech_gradient_blue` — 科技蓝·计算生物版

Use for AI, bioinformatics, spatial omics, methods, and model-development papers. Restrict blue gradients to the cover or Results dividers; evidence slides remain predominantly white with blue rules and large plots. Prefer `compact + mixed`.

### `black_red_conference` — 黑白红·学术会议版

Use for concise conference reports and one-claim-per-slide evidence sequences. Keep the canvas white, typography black, and reserve red for one active emphasis, section number, or statistically grounded callout. Never recolor scientific data to match the accent. Prefer `standard + panel_first`.

## User-facing style catalogue

Offer Chinese labels rather than internal ids when the user wants to choose:

- Nature 墨绿·组会精讲版 — current validated green baseline;
- 科研蓝·高密度导航 — dense biomedical Results decks;
- 医学院·蓝色简约 — defenses, mid-term reports, and institutional talks;
- 期刊白·极简图证 — one decisive experiment per slide;
- Nature 编辑部·杂志风 — sparse cross-disciplinary editorial storytelling;
- 暖米白·综述杂志版 — reviews and conceptual synthesis;
- 科技蓝·计算生物版 — methods, AI, bioinformatics, and omics;
- 单色高级·紫/青/酒红 — restrained personal accent variants;
- 黑白红·学术会议版 — concise formal conference reporting;
- 深色影像·显微优先 — dark-field imaging-dominant studies.

The catalogue is informed by the user's previously reviewed Xiaohongshu scientific-presentation references, but each option must be implemented as an academic system rather than copying a social-media template or its assets.

## Automatic recommendation

Apply this order:

1. User-provided reference deck or explicit preset.
2. User requests the approved green version or a reference-led biomedical journal club → `nature_green_journal_club`.
3. Formal institutional requirement → `clinical_blue`.
4. Majority dark-field evidence → `dark_imaging`.
5. AI, omics, or methods talk with process-heavy evidence → `tech_gradient_blue`.
6. Cross-disciplinary synthesis with sparse Figures → `editorial_nature` or `warm_beige_review`.
7. One-result-per-slide, low panel count → `journal_white`.
8. Dense multi-panel biomedical paper → `academic_blue_nav`.
9. Explicit request for purple/teal/burgundy restraint → `mono_accent`.
10. Explicit formal black/red conference direction → `black_red_conference`.

When two presets remain plausible, generate two representative slides from the same evidence map before building both full decks.

## Locked layout registry

Use these named archetypes. Each preset lists the subset it permits.

- `L01_cover_minimal`: citation-led cover with no evidence claim.
- `L02_question_context`: problem, gap, and paper question.
- `L03_method_flow`: study design or reproducible workflow.
- `L04_figure_full_takeaway`: one readable panel/group plus one interpretation strip.
- `L05_figure_sidebar_metrics`: dominant panel plus exact metrics or cohort facts.
- `L06_paired_panels`: two scientifically comparable panels with shared context.
- `L07_full_figure_map`: brief overview of a compound Figure before detailed crops.
- `L08_limitations`: bounded limitations, bias, or failure modes.
- `L09_synthesis`: main results, study scope, limitations, and conclusion.
- `L10_section_bridge`: optional short section transition for decks longer than 12 slides.
- `L11_narrow_panel_zoom_strip`: one accepted tall or wide compound panel represented as two to three disclosed zoom fragments arranged across the long slide axis; preserve one panel identity, required labels, axes, legends, and source lineage.

Do not invent a new layout merely for visual variety. Add a new archetype only when existing layouts cannot preserve a recurring scientific relationship.

## Density contracts

### `compact`

- Slide title: at least 35 pt.
- Body: at least 16 pt.
- Figure/panel area: target 62–78% of usable canvas.
- At most two primary scientific panels or one panel plus metrics.
- At most four short audience-facing statements.

### `standard`

- Slide title: 38–44 pt.
- Body: 18–22 pt.
- Figure/panel area: target 58–72%.
- One dominant Figure group; a second asset only for direct comparison.

### `airy`

- Slide title: 42–50 pt.
- Body: 20–24 pt.
- Figure/panel area: target 48–65%.
- One claim and one dominant visual.

Shorten text or change layout before shrinking type.

## Evidence-frame occupancy gate

- Compute projected asset and scientific-content fill with `scripts/audit_evidence_fill.py` before finalizing an evidence layout.
- Reroute when asset fill is below `0.45` or scientific-content fill is below `0.35`.
- Use `L11_narrow_panel_zoom_strip` only when the accepted panel contains separable internal result regions. Treat each zoom as a continuation, not a new panel.
- Prefer a full-panel locator plus zooms when spatial order matters. Prefer a zoom strip when internal plots are read sequentially and share one local claim.
- Do not stretch scientific rasters, crop required context, or fill space with extra prose or decoration.

## Scientific Figure rules

- Keep panel label, axes, legends, scale bars, statistical marks, cohort labels, and required shared assets readable.
- Use `contain` by default. Crop only through the accepted panel manifest.
- Put annotations beside the Figure. Do not paint over source data.
- Use a full Figure only when cross-panel relationships are the evidence.
- Keep source notes and manifest lineage identical across A/B style variants.

## Inspiration and licensing boundary

The production pattern may learn from open-source presentation systems that use finite presets, locked layouts, plan contracts, and rendered QA. Reimplement all styles and validators locally. Do not copy Guizang PPT templates, assets, CSS, or code into this Skill; its upstream repository is AGPL-3.0. Treat external templates as visual research unless their license and attribution requirements are deliberately adopted.
