# Detector routing

Use the lowest-risk route that preserves scientific context. Do not describe a document parser as a panel detector.

## Route order

1. **Publisher asset**: prefer an independent, full-resolution Figure.
2. **PDF structure**: use PDF text/image/vector blocks to locate the Figure and caption.
3. **Panel proposal**:
   - use FigEx or another compound-scientific-Figure detector when locally configured;
   - otherwise use active-Codex visual proposals grounded by the rendered Figure;
   - use geometry/separator heuristics only as additional evidence.
4. **OCR/layout evidence**: use a configured PaddleOCR, PaddleOCR-VL, MinerU, or Docling route to locate panel letters, axes, legends, and nearby text. Record the exact route and version when observed.
5. **Caption alignment**: split the source caption conservatively and match labels/cohorts/conditions to boxes.
6. **Refinement**: use SAM-style segmentation only inside an already accepted proposal when a non-rectangular object boundary is needed. Do not use SAM to define the scientific panel taxonomy.
7. **Visual judge**: inspect the source with overlays and crops at full resolution.

## Evidence strength

- Strong: publisher bbox/object + explicit label + caption match.
- Moderate: two independent visual/layout proposals + caption/cohort match.
- Weak: one VLM bbox, OCR label alone, separator whitespace alone, or unlabeled visual grouping without caption support.

Auto-accept only strong or independently corroborated moderate proposals. Keep weak proposals as `needs_review`.

## PDF/OCR boundaries

- PDFFigures-style tools locate whole Figures and captions; compound subfigures remain a downstream problem.
- MinerU, Docling, PaddleOCR-VL, and OCR systems provide page layout and text grounding; they do not by themselves prove panel boundaries.
- FigEx-like models target compound Figure panel boxes and caption alignment, but must still pass crop QA on the actual paper domain.
- OCR may miss small italic labels or confuse `I/l/1`; reconcile with caption labels and reading order.

## Privacy and provider policy

Keep local papers local by default. Before sending PDF pages, Figures, captions, or crops to a remote or paid provider, obtain explicit user authorization and record provider, model, request count, and transmitted scope. Never print credentials.

If no specialized detector is configured, continue with a disclosed `codex_visual + source_text + manual_review` route rather than claiming FigEx/OCR execution.
