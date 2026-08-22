# Evaluation

Evaluate the panel pipeline separately from the slide design.

## Argument and notes metrics

- `paper_digest.json`, `argument_map.json`, `figure_claims.json`, and `speaker_notes.json` exist and are internally consistent.
- Every evidence-slide title is entailed by the displayed evidence and preserves the study boundary.
- Every inserted Figure/panel has a recorded question, design, observation, inference, limitation, and argument link.
- Every visible and spoken number is source-verified.
- Association, prediction, prognosis, mechanism, and causation are not conflated.
- Speaker notes use natural oral Chinese, define first-use terms, contain a transition, fit the time budget, and end with `[Sources]`.
- Each evidence-note `covered_panels` set equals the slide plan's `panel_refs`; adjacent split-panel slides do not contain duplicated normalized scripts.
- Manuscript facts, author interpretation, presenter interpretation, clinical implication, and speculation remain distinguishable.
- In `full_main_figures`, every authoritative expected panel has a Results assignment, complete explanation, slide-plan entry, and source lineage.

## Contract and style metrics

- `style_spec.json` passes the bundled validator.
- Every slide uses a layout permitted by the selected preset.
- Density stays inside the preset contract without sub-minimum type.
- Palette and accent variant match the registered preset.
- Adjacent slides vary silhouette without switching visual systems.
- A/B variants preserve identical scientific claims, accepted panel pixels, and source notes.
- Native slide text, annotations, and simple shapes remain editable; no full-slide raster is mislabeled as editable.
- When a reference PPTX defines language style, section labels, title syntax, result verbs, and terminology follow the audited reference-language contract even if the visual preset differs.

## Panel metrics

- Figure retrieval correctness.
- Expected/produced panel count.
- Panel-label accuracy.
- Panel-caption or cohort alignment accuracy.
- Boundary completeness: subject, axes, legends, scale bars, and statistics.
- Duplicate/overlap rate.
- Final-slide readability.
- Manual corrections per Figure.
- Authoritative main-panel coverage: accepted or disclosed status divided by caption/artwork-derived expected labels.

IoU alone is insufficient: a geometrically high-overlap crop can still remove the y-axis, legend, or scale bar.

## Visual review

Inspect, at full size:

1. frozen source Figure;
2. overlay review;
3. every accepted crop;
4. contact sheet;
5. every final slide containing the crop.

Record independent results for labels, assets, axes/legends, caption pairing, and layout.

For `full_main_figures`, also inspect the closing one or two slides as a route map. They should connect cohort or source material, assays or data, derived variables, analysis or model construction, and validation without inventing convergence between parallel branches. Fail a generic limitations-plus-conclusions ending when it does not help the audience reconstruct the paper's full argument.

For every evidence slide, also record `projected_asset_fill_ratio` and `projected_content_fill_ratio`. Fail the slide when a dominant evidence frame is below `0.45` asset fill or `0.35` scientific-content fill, unless the remaining frame is intentionally occupied by another scientifically necessary asset. A source-faithful but tiny plot centered in a large empty frame is not a passing layout.

## Failure labels

- `wrong_figure`
- `missing_panel`
- `extra_panel`
- `label_mismatch`
- `caption_mismatch`
- `clipped_axis`
- `clipped_legend`
- `clipped_scale_bar`
- `clipped_subject`
- `shared_asset_orphaned`
- `inset_detached`
- `low_resolution`
- `underfilled_evidence_frame`
- `unverified_remote_result`

## Delivery claim

Use `panel_verified` only when every inserted panel passed the manifest and final-slide gates. Use `argument_verified` only when every title, Figure explanation, and spoken statistic passed the interpretation gates. Use `figure_level_only` when compound Figures were not reliably split. Use `partial_review_required` when any inserted crop or interpretation still needs user confirmation.

Report the final `style_id`, `density`, and `figure_layout`. A visually polished deck does not upgrade an unverified crop.

For rule-only tests, do not report a deck delivery claim. Use the decision labels in [dry-run-evaluation.md](dry-run-evaluation.md) and name all untested stages.
