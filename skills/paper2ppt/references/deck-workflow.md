# Evidence-led deck workflow

## Planning contract

Before authoring, freeze seven machine-readable files:

- `deck_brief.json`: audience, purpose, duration/page target, paper type, language, editability requirement, and hard constraints.
- `style_spec.json`: validated visual preset, density, Figure treatment, and branding.
- `paper_digest.json`: source-grounded problem, design, results, terminology, limitations, and exact locations.
- `argument_map.json`: question → claim → evidence → warrant → scope → limitation → next claim.
- `figure_claims.json`: per-Figure or per-panel role, design, read order, observation, inference, boundary, and lineage.
- `coverage_contract.json`: coverage mode, exact Results ledger, authoritative panel inventory, panel-to-claim mapping, slide-plan coverage, notes coverage, and exceptions.
- `deck_plan.json`: slide id, assertion title, role, claim, warrant, scope, evidence assets, source lineage, layout id, visible-copy budget, notes purpose, and expected visual hierarchy.
- `speaker_notes.json`: timed oral Chinese script, transition, first-use terminology, and sources for every substantive slide.

When a user provides a reference PPTX for language, density, or notes, read [reference-language-notes.md](reference-language-notes.md). Add `covered_panels` to each evidence-slide note and validate the notes against `deck_plan.json` before authoring.

Choose layout ids only from [style-system.md](style-system.md) and the validated preset. Keep planning data separate from the PPTX renderer so an A/B style test can reuse the same claims and accepted panel assets. For `full_main_figures`, validate [precision-journal-club.md](precision-journal-club.md) before authoring.

## Communication job

For a default journal club, make the audience understand the paper's question, design, strongest evidence, how each Figure advances the argument, uncertainty, and practical implication. Adapt for the user's audience and purpose when specified.

## Paper-type arcs

- `discovery`: question → mechanism hypothesis → evidence chain → validation → boundary.
- `methods`: reproducibility/problem → proposed workflow → implementation → benchmark/use cases → limitations → adoption.
- `resource`: unmet need → resource construction → coverage → validation → access/reuse.
- `clinical`: clinical question → design/population → endpoint → effect and uncertainty → safety/bias → applicability.
- `materials`: design principle → fabrication/characterization → performance → mechanism → durability/generalization.
- `review`: scope → evidence map → agreement/conflict → gaps → practical synthesis.

## Default 9-12 slide structure

1. Minimal title and citation.
2. Research background and reproducibility problem.
3. Study objective and design.
4. Study design or workflow Figure.
5-8. One evidence claim per slide with a readable panel or semantic group.
9. Robustness, limitations, or failure modes.
10. Main findings, study scope, limitations, and conclusion.

Do not add an agenda unless the deck is long enough to benefit.

This default applies only to `selective` mode. In `full_main_figures`, panel coverage determines slide count; do not compress the paper into 9–12 slides by omitting panels.

## Slide copy

- Default to a neutral academic-reporting register for journal clubs, lab meetings, and conference presentations.
- Evidence-slide titles should state the source-grounded result or scoped inference that the displayed evidence supports. Prefer forms such as `N=421 扩展队列中 AUC 降至 0.61` over rhetorical questions, slogans, metaphors, promotional claims, or generic section labels.
- Use conventional academic section labels where useful: `研究背景`, `研究目的`, `研究设计`, `主要结果`, `局限性`, `结论`.
- Do not use production-language headings such as `关键点`, `为什么重要`, `被支持`, `尚未被支持`, or `下一步` unless the user explicitly requests a critical-appraisal or teaching format.
- Distinguish reported results from presenter interpretation. Put interpretation in a clearly labeled discussion block or speaker notes; do not phrase it as a source result.
- Keep visible Chinese text concise and audience-facing.
- Put methodological detail, exact statistics, and explanation in speaker notes when it would crowd the slide.
- Preserve gene/protein names, datasets, metrics, abbreviations, N values, units, and statistical notation exactly.
- Add a `[Sources]` block to speaker notes for every paper Figure and nontrivial claim.
- Speaker notes must follow [paper-interpretation.md](paper-interpretation.md): reading coordinate → observation → interpretation boundary → transition.
- Do not copy one complete script onto adjacent slides that split the same Figure. Each script must correspond only to the panels visible on that slide.

When the user supplies a reference PPTX for language, treat its copy style as a separate contract from its visual style. Inspect the full deck's section labels, title syntax, result verbs, terminology, sentence length, and figure annotations before writing. Reproduce the rhetorical pattern rather than copying subject-specific wording. For a formal biomedical reference that uses titles such as `利用 X 可抑制 Y` or `联合分析提示 X 与 Y 相关`, prefer the same direct research-action/result syntax over production labels such as `分析路线`, `证据模块`, `数据产物`, or compressed chains of English keywords.

## Figure placement

- Prefer one panel or one coherent semantic group per evidence slide.
- Show the full Figure briefly only when relationships among panels are the evidence.
- Never crop a shared legend away; duplicate a disclosed shared legend or keep the relevant panels together.
- Do not enlarge a low-resolution crop past readability; reacquire the source or use a larger semantic group.
- Add presentation annotations beside the Figure; do not paint over source data.
- Measure projected evidence-frame use before committing the layout. Run `scripts/audit_evidence_fill.py` with the actual accepted raster and frame dimensions. A projected asset fill below `0.45` or projected scientific-content fill below `0.35` is a hard reroute, not an aesthetic warning.
- For a tall or wide compound panel, keep the accepted panel identity and source lineage, then use `L11_narrow_panel_zoom_strip` or a locator view plus disclosed zoom fragments. Label fragments as continuations of the same Figure panel; do not count them as new panels.
- If internal boundaries are unsafe, pair the panel only with evidence answering the same local question, or reacquire a tighter source. Never solve underfill by distortion, by removing axes/legends/sample sizes, or by adding filler prose, decorative cards, or unrelated images.

## Style application

- Apply style only after panel manifests and the claim-evidence table are stable.
- Use the validated preset palette and layout registry; do not mix visual systems within one deck.
- Reuse the same slide ids, claims, evidence assets, and source notes for A/B variants.
- Prefer finite layout archetypes over improvised card collections.
- Preserve editability for titles, annotations, takeaways, and simple shapes. Keep scientific raster evidence as source-faithful images.

## Closing sequence for full-paper explanation

For `full_main_figures` and other full-paper explanation decks, use the final one or two slides to replay the paper's end-to-end technical or evidence route. Prefer the paper's own study-design or workflow Figure when it already provides that overview. If no single overview Figure exists, reconstruct a source-grounded route from cohort and specimens through assays or data sources, derived measures, analysis or model development, validation cohorts, and the final supported conclusion.

If the paper also contains an author-supplied visual abstract or integrated mechanism Figure, use the reconstructed technical route as the penultimate recap and the original visual abstract as the final slide. Do not replace a readable source visual abstract with a simplified reconstruction, and do not put either overview before Results unless the user explicitly requests a preview-first talk.

Do not end a precision journal club with two generic list slides that merely restate limitations and conclusions. When critical appraisal is not the presentation's main purpose, keep the principal evidence boundary as a concise footer or in speaker notes so the closing route remains the dominant visual. The reconstructed route must preserve sample sizes, platform-specific coverage, training and validation splits, and any branch that does not actually enter the final model.

## PPTX QA

Use the installed Presentations workflow and required runtime. Render every slide. Fix all unintended overlap, clipping, wrapping, unreadable labels, and inconsistent source notes before delivery.

Run the style-spec validator before authoring and again before final delivery. Compare the rendered deck against the selected preset's density contract and permitted layout silhouettes.
