# Rule-only dry-run evaluation

Use this route when the user wants to define or test the Skill without producing a PPTX.

## Output scope

Create only:

- `paper_digest.json`;
- `results_ledger.json`;
- `coverage_contract.json`;
- per-Figure `panel_manifest.json`, overlay, crops, and contact sheet when panel precision is under test;
- `results_figure_map.md`;
- `speaker_notes_sample.json` with at least three contrasting examples;
- `dry_run_report.md`.

Do not create a PPTX, style mockup, or final deck render unless the user separately authorizes authoring.

## Test depths

- `rules_only`: validate schema, triggering, coverage modes, and hard gates with no crop production.
- `panel_test`: materialize all in-scope panel proposals and review boundaries at full size.
- `content_test`: map every panel to Results, claims, slide-plan entries, and at least three oral-note samples.
- `full_preflight`: complete all pre-authoring artifacts and notes, but stop before PPTX creation.

Use `panel_test + content_test` by default when a real paper is supplied and the user asks whether the Skill works.

## Metrics

Report numerator, denominator, and failed ids for:

- authoritative expected-panel coverage;
- accepted crop coverage;
- panel-label accuracy;
- caption/panel alignment;
- Results-section assignment;
- complete panel-explanation coverage;
- planned-slide coverage;
- source-lineage completeness;
- oral-note sample compliance.

Do not average these into one flattering score. A 100% mean can hide a missing panel. Report each gate independently.

## Decision labels

- `ready_for_authoring`: all hard gates pass.
- `ready_after_manual_crop_review`: content gates pass; named crop boundaries remain unresolved.
- `rules_pass_panel_test_incomplete`: rules and mapping pass, but full crop review was not run.
- `not_ready`: one or more coverage, mapping, claim, or lineage gates fail.

The report must state what was actually tested and what remains untested.
