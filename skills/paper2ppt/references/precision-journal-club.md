# Precision journal-club contract

Use this contract for 精讲, 逐图讲解, 主图全部 panel, or equivalent requests. It prevents a selective-summary deck from being presented as a full paper explanation.

## 1. Lock the coverage mode

Record one mode in `coverage_contract.json`:

- `selective`: selected evidence only;
- `full_main_figures`: every labeled panel in every main-text Figure;
- `all_figures`: main, Extended Data, and Supplementary Figures.

Default 精讲 to `full_main_figures`. A page limit does not authorize panel omission; increase slide count, combine compatible panels, or ask the user to relax coverage.

## 2. Build the authoritative panel inventory

Derive expected labels from the full caption, Figure artwork, and Results references. Record all three sources and resolve disagreements explicitly. Treat a caption sequence such as `a–g` as seven expected panels. Do not promote unlabeled subplots inside a labeled panel to independent panels unless the caption or scientific reading requires it.

For every in-scope Figure record:

- Figure number, caption, Results subsection, and scientific role;
- expected labels and produced labels;
- panel status: `accepted`, `needs_review`, or `exception`;
- source bbox, caption segment, required shared assets, and review note.

Coverage is calculated against the authoritative expected-label set, not against the crops the pipeline happened to produce.

## 3. Use Results subsections as the argument spine

Create an ordered Results ledger from the paper's exact subsection headings. Each panel receives one primary `result_section_id`; secondary links are optional. Preserve the exact English source heading in planning data and provide a faithful Chinese section label.

Use the paper's Results subsections as the visible chapter hierarchy. When the selected reference deck uses dedicated chapter dividers, render each Results subsection as a large divider and keep only one panel-specific assertion title on subsequent evidence slides. Do not repeat a second micro-heading on every evidence slide merely to restate the chapter name. When no divider is used, a compact Results anchor may remain above the assertion title.

The Results chapter label must be visually larger and more prominent than utility labels, page numbers, Figure tags, and footers. Evidence-slide titles state the local observation or scoped inference supported by the visible panels.

Do not use only `Figure 3`, `主要结果`, `关键发现`, or a generic question as the slide title. Do not force a stronger claim than the panel supports merely to make the title sound decisive.

## 4. Explain every panel

Every panel must have a claim record with:

- `question`: why the authors needed this panel;
- `design`: cohort, comparison, assay/model, endpoint, and statistic;
- `read_order`: where the audience should look first;
- `observation`: exact visible result, with direction and uncertainty when shown;
- `author_inference`: the interpretation stated by the paper;
- `presenter_explanation`: how the panel advances the paper's argument;
- `presenter_boundary`: what it does not establish;
- `next_link`: why the next panel or Results subsection follows;
- `source_lineage`: panel, caption segment, Results paragraph, and asset.

Descriptive, negative, quality-control, and bridge panels still require an explanation. Do not omit them because they are less dramatic.

## 5. Plan slides without hiding panels

Every expected panel must appear in at least one planned evidence slide. A panel may appear twice when a full-Figure overview is followed by a readable close-up; count it once for coverage. Combine panels only when they answer the same local question and remain readable at the final slide size.

Dense panels may occupy more than one slide through disclosed zooms. Preserve the panel label and identify zoom slides as continuations; never count zoom fragments as new panels.

When two adjacent slides are needed to explain one local conclusion, the assertion title may remain identical. The notes and visible panel set must still be specific to each page.

## 6. Write objective oral notes

Speaker notes follow this oral sequence:

1. identify the scientific question and panel coordinate;
2. state design and comparison;
3. tell the audience how to read the panel;
4. report the observation and only essential statistics;
5. distinguish the authors' interpretation from the presenter's explanation;
6. state the evidence boundary;
7. transition to the next claim.

Use neutral academic Chinese. Avoid promotional adjectives, rhetorical hooks, fake surprise, slogan-like contrast, and phrases such as `这张图告诉我们一个非常重要的故事`. Prefer direct reporting: `图 2d 显示……；作者据此认为……；但该结果仍属于相关性证据。`

For a Figure split across adjacent slides, each note covers only that slide's visible panel set. Reusing the same sources is allowed; reusing the same complete spoken script is a validation failure.

## 7. Close by reconstructing the full route

After all required panels have been explained, reserve the final one or two slides for an end-to-end technical or evidence-route recap. In a full-paper explanation, do not place the complete technical-route diagram before the Results chapters unless the user or reference explicitly requires an early methods overview. Reuse a source study-design Figure when it is suitable; otherwise synthesize the route from verified manuscript details. Show how the cohort and specimens produce each assay, how each derived variable supports the next analysis, which branches converge in the final score or conclusion, and where internal or external validation occurs. When the paper also supplies a readable visual abstract or integrated mechanism Figure, the reconstructed route is penultimate and the original source visual abstract is the final slide.

Do not imply that every intermediate feature enters the final model. Keep parallel or supporting branches separate when the paper does. A compact evidence-boundary line may replace a full limitations slide unless the user explicitly asks for a critical-appraisal ending.

## 8. Hard gates

`full_main_figures` passes only when:

- expected-panel coverage is 100%;
- every panel is assigned to a Results subsection;
- every panel has a complete claim record and source lineage;
- every panel appears in the slide plan;
- every evidence slide has a Results anchor and assertion title;
- when dedicated Results dividers are used, the divider plus the evidence-slide assertion title satisfies the hierarchy requirement; a repeated micro-anchor is not required;
- every substantive slide has notes before PPTX authoring;
- accepted crops preserve labels, axes, legends, scale bars, sample sizes, and statistical annotations;
- every exception and low-confidence crop is disclosed.
- the closing sequence reconstructs the paper's technical or evidence route instead of ending with generic conclusion and limitation lists.
- no visible production label such as `解释边界` or `证据边界` is introduced unless it appears in the user-approved reference; evidence limits normally belong in the speaker notes.

If any gate fails, report the missing panel ids and stop before PPTX authoring.
