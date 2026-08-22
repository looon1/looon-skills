# Formal academic language and speaker-note contract

Use this contract when a user supplies a presentation as a language, density, or speaker-note reference. Treat the rhetorical system separately from the visual preset: a reference can govern wording and oral delivery without replacing the requested visual style.

## 1. Audit the complete reference

Inspect every slide and every notes page. Record:

- section hierarchy and chapter count;
- title syntax and evidence verbs;
- visible Figure-to-text ratio and takeaway placement;
- note length, paragraphing, terminology, reading order, evidence boundary, and transition;
- repeated or missing notes that should not be copied.

Learn the pattern, not the paper-specific wording. Do not preserve errors merely because they occur in the reference.

## 2. Results-led chapter structure

- Use the paper's Results subsections as the major chapters.
- Keep one stable subsection anchor across consecutive evidence slides.
- Do not add a new micro-heading for every method, panel, or interpretation.
- Use the slide title for the panel-specific result; use notes for method explanation and interpretation.
- Add a section divider only when it materially improves navigation in a long deck. A divider is not evidence coverage.
- If a supplied reference uses prominent chapter dividers, make the Results number and subsection heading the dominant typography on those dividers; evidence slides then use one conclusion title without a second repeated micro-heading.
- Do not add visible meta-language such as `解释边界`、`证据边界`、`本页结论` or `讲解要点` unless the supplied reference contains it. Put necessary caution in the oral notes as ordinary academic prose.

## 3. Assertion-title register

Write titles as objective result sentences. Name the object, comparison, direction, and evidence boundary when space permits.

Prefer calibrated verbs:

- direct observation: `显示`、`升高`、`降低`、`富集于`、`与……相关`;
- repeated or corroborating evidence: `支持`、`保持一致`、`得到验证`;
- model-based or indirect evidence: `提示`、`预测`、`与……相符`;
- causal language: use only for an intervention or design that establishes causality.

Avoid praise, novelty claims, rhetorical questions, slogans, and inflated wording such as `重磅发现`、`惊人机制`、`深入揭示`、`关键突破` or `这张图讲了一个重要故事`.

If the notes contain a limitation such as `仅为计算预测` or `仍需实验验证`, the title must not state the relationship as established mechanism or causation.

## 4. Evidence-slide density

For a panel-led academic slide:

- allocate roughly 60–75% of the usable canvas to one dominant panel or a coherent panel pair;
- place one or two short panel-matched result statements in a stable takeaway strip or adjacent interpretation zone;
- do not place a small scientific plot in a large empty frame;
- use a locator-plus-zoom or disclosed zoom strip for narrow compound panels;
- do not fill whitespace with generic prose, decorative cards, or unrelated images.
- project the final on-slide size before authoring. If axis labels, legends, group names, or statistical marks would be hard to read, split the panel set across additional slides or use a disclosed locator-plus-zoom layout. Never keep an unreadable three-column panel arrangement solely to reduce slide count.

The visible statement identifies what the audience should conclude. The notes explain how to read the evidence.

## 5. Oral-note sequence

Each substantive slide's `script_zh` should sound like a formal lab-meeting or conference explanation and normally follow this sequence without exposing labels:

1. locate the visible Figure panel and state its design or comparison;
2. tell the audience where to look first, second, and third;
3. report the principal observation and only essential statistics;
4. state what the result supports in the local argument;
5. state the evidence boundary when the claim could be over-read;
6. end with a natural reason for the next analysis.

Use compact spoken sentences such as `图 2d 展示……`、`先看左侧……`、`结果显示……`、`这一结果支持……`、`需要注意……` and `随后作者进一步检验……`. Vary sentence structure; do not mechanically repeat every phrase on every slide.

Ordinary evidence slides usually need 140–300 Chinese characters or about 45–90 seconds. Method-heavy slides may use 300–480 characters when the extra text explains how to read an unfamiliar analysis. Covers and section dividers may be shorter.

## 6. Panel-to-note exclusivity

- Add `covered_panels` to every evidence-slide note.
- Its set must equal the slide plan's `panel_refs`.
- Discuss only panels visible on that slide. A brief reference to the preceding result is allowed solely to establish continuity.
- When adjacent slides split one Figure, do not duplicate the full script. Give each page its own design, reading coordinate, observation, boundary, and transition.
- Repeated sources are allowed; repeated spoken scripts are not.

## 7. Source attribution and final form

Keep the spoken script as uninterrupted presenter-ready prose. Do not insert production labels such as `[Transition]`, `[Terms]`, `speaker cue`, or `talk track` into the oral section. Append only the required source block after the script:

```text
[Sources]
- Main paper: DOI ..., Fig. ..., Results ...
```

Use `本研究` or `作者` when attribution matters. Do not silently turn a presenter interpretation into an author conclusion.

## 8. QA gates

Before authoring, run `scripts/validate_speaker_notes.py`. Then inspect the notes inside the exported PPTX and verify:

- every substantive slide has a nonempty script and sources;
- `covered_panels` matches the slide plan;
- no two substantive slides have identical normalized scripts;
- ordinary scripts are within the spoken-length budget or carry an explicit exception;
- panel-specific statistics, terms, and evidence boundaries agree with the source;
- the final spoken sentence advances to the next scientific question rather than announcing production steps.
