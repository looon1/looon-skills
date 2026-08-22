# Paper interpretation and oral-report contract

The deck is an argument reconstruction, not a sequence of screenshots. Do not author slides until the paper digest, argument map, Figure claims, and oral notes have been grounded in the source.

## 1. Paper digest

Create `paper_digest.json` with:

- full citation, DOI/PMID, article type, access route, and source checksum;
- research problem, prior knowledge, unresolved gap, and study objective;
- study design, population/material, modalities, comparisons, endpoints, and validation strategy;
- main claims with exact source locations and statistics;
- author-stated limitations, presenter-identified interpretation boundaries, and unresolved questions;
- terminology ledger for abbreviations, gene/protein names, cohorts, scores, and statistical measures.

Use `[UNVERIFIED]` for any fact that cannot be traced. Do not infer missing cohort sizes, directions, thresholds, or causal claims.

## 2. Argument map

Create `argument_map.json`. Each node must contain:

```json
{
  "id": "C1",
  "question": "What scientific question is being answered?",
  "claim": "A source-grounded result or scoped inference",
  "evidence": ["Fig. 1d", "Results paragraph 3"],
  "warrant": "Why the evidence supports the claim",
  "scope": "Population, condition, endpoint, and design boundary",
  "limitations": ["What the evidence does not establish"],
  "depends_on": ["C0"],
  "leads_to": ["C2"]
}
```

Separate five levels explicitly: `reported_observation`, `author_interpretation`, `presenter_interpretation`, `clinical_implication`, and `speculation`. Only the first two may appear as unqualified study conclusions.

## 3. Figure claim record

Create `figure_claims.json`. For every Figure or selected panel, record:

- `figure_role`: why the Figure exists in the paper's argument;
- `question`: the question the panel addresses;
- `design`: cohorts, groups, assay, model, endpoint, and statistical comparison;
- `read_order`: what the audience should inspect first, second, and third;
- `observation`: exact direction, magnitude, uncertainty, and sample size when shown;
- `author_inference`: the paper's stated interpretation;
- `presenter_explanation`: how this panel advances the local Results claim and the paper's overall argument;
- `presenter_boundary`: what the panel cannot establish;
- `argument_link`: which prior claim it depends on and which next claim it motivates;
- `source_lineage`: Figure/panel, caption segment, page/section, and asset path.

Do not summarize a multi-panel Figure as one conclusion unless every displayed panel supports that same conclusion. If a panel is only descriptive, label it descriptive rather than causal or prognostic.

In `full_main_figures` mode, create one record for every expected main-Figure panel, including descriptive, negative, validation, and bridge panels. See [precision-journal-club.md](precision-journal-club.md).

## 4. Slide title contract

Evidence-slide titles are assertion headlines: one sentence that states the central source-grounded result shown on the slide.

Good titles name the object, comparison, direction, and boundary when space permits:

- `ICR 高表达组的总生存和无进展生存更长`
- `肿瘤富集 T 细胞克隆与 ICR 呈正相关`
- `mICRoScore 在独立 TCGA 队列中保持预后分层`

Avoid manuscript labels (`Results 1`), generic headings (`关键发现`), questions, slogans, praise, novelty language, and claims stronger than the displayed evidence. A title must be editable downward if the evidence supports only association, not mechanism or causality.

## 5. Speaker-note contract

Create `speaker_notes.json` before PPTX authoring. Each substantive slide contains:

```json
{
  "slide_id": "S05",
  "purpose": "What this slide must establish",
  "duration_seconds": 60,
  "script_zh": "Natural spoken Chinese",
  "transition": "One sentence connecting to the next claim",
  "covered_panels": ["fig2b", "fig2c"],
  "terms": [{"term": "ICR", "first_use": "immunologic constant of rejection，免疫排斥常数"}],
  "sources": ["DOI ... Fig. 2b", "PDF p. ..."]
}
```

Write for the ear:

- start with the scientific question or reading coordinate, not a rhetorical hook;
- describe how to read the panel before interpreting it;
- state only the one or two statistics needed to anchor the conclusion;
- distinguish observation from interpretation with explicit wording;
- define an abbreviation at first oral use;
- end with the reason the next slide is needed;
- use neutral academic Chinese, short breath-length sentences, and conventional terminology;
- do not use promotional adjectives, metaphors, fake quotations, audience manipulation, or AI-style antitheses;
- do not repeat every number already visible on the slide;
- never introduce a number, cohort, mechanism, or clinical recommendation absent from the source.

Target 45–90 seconds for an ordinary evidence slide unless the deck brief specifies another pace. Read the script aloud and revise sentences that cannot be spoken in one breath.

Every notes block ends with:

```text
[Sources]
- Main paper: DOI ..., Fig. ..., page/section ...
- Supporting source: DOI/PMID ... [only if actually used]
```

When a reference presentation supplies the language or oral-report baseline, also apply [reference-language-notes.md](reference-language-notes.md). Preserve panel-to-note exclusivity: notes for a split Figure must be rewritten per slide rather than duplicated.

## 6. Interpretation QA

Before delivery, verify:

1. every action title is entailed by its displayed evidence;
2. every Figure has a recorded role, question, observation, inference, and boundary;
3. every visible statistic and every spoken statistic matches the source;
4. association, prediction, prognosis, mechanism, and causation are not conflated;
5. validation claims name the validation cohort and its limits;
6. limitations distinguish author statements from presenter assessment;
7. every transition follows the argument map rather than manuscript pagination;
8. speaker notes are complete, timed, orally natural, and source-linked.

## Method lineage

This contract incorporates compatible ideas from three MIT-licensed open-source skill families reviewed in August 2026: Aperivue `medsci-skills/present-paper` (paper analysis, scripts, notes, Q&A), seabbs `skills/analyzing-research-papers` (section-level extraction and methodological boundaries), and luwill `research-skills/scholar-slides` (typed digest, action titles, integrity gates, per-slide specs, and speaker-note QA). The local implementation remains panel-aware and uses its own manifests, renderer, and evaluation gates.
