---
name: illustrator-flowchart-drawing
description: Reconstruct scientific and technical workflow images as validated editable SVGs by drawing text, lines, arrows, frames, and simple shapes natively while routing only complex illustrations through a private SuperSVG server. Use for flowcharts, mechanism diagrams, scientific workflows, graphical abstracts, and optional Adobe Illustrator playback. Linux supports SVG generation without Illustrator.
---

# Illustrator流程图绘制

Use this pipeline:

`scene manifest -> direct native rules for text/lines/arrows/frames/basic shapes -> crop only complex semantic assets -> private SuperSVG per complex asset -> hybrid Master SVG -> lossless geometry cache -> optional Illustrator playback`

Read [references/workflow.md](references/workflow.md) for ordinary execution. Read [references/server-runtime.md](references/server-runtime.md) only for server startup or diagnostics, and [references/illustrator-runtime.md](references/illustrator-runtime.md) only when drawing into Illustrator.

## Essential boundaries

- The only vector model is self-hosted `JTUplayer/SuperSVG`. Use tiled inference when a complex crop needs additional spatial detail and enable fine-tuning (`optimize_iter >= 10`) in quality mode. SAM3 is optional and may produce foreground contours for complex-asset clipping; it never performs vectorization and must never receive rule elements.
- The private server is reached through SSH by default. Do not expose the GPU service publicly or send images to third-party vector services.
- SuperSVG is only for complex semantic assets such as animals, cells, organelles, textured proteins, molecular illustrations, and irregular scientific icons. It must never receive text, lines, arrows, connectors, axes, frames, panels, timelines, or other rule-based primitives.
- Text, straight or polyline connectors, arrow shafts/heads, frames, panel backgrounds, axes, circles, ellipses, rectangles, and simple polygons are created directly as editable SVG/Illustrator objects from the Scene Manifest.
- Whole-frame model vectorization is not supported. A Scene Manifest is mandatory so rule elements can never be routed through SuperSVG.
- Quality is a hard gate. Never reduce path count, simplify curves, discard paint parts, flatten gradients, remove clipping or masks, or downscale the accepted source merely to make Illustrator playback faster. Optimize transport, batching, checkpoints, and caching only.
- Keep the untouched reference. Extract all visible text and build an object-level Scene Manifest before any model call.
- Always validate every complex-asset SVG, the Scene Manifest, and the final hybrid Master SVG before caching or drawing.
- Never use local Image Trace, Potrace, OpenCV contours, raster wrappers, or hand-authored substitutes for a required fresh model result.

## First-use preflight

Install the managed environment once, then run the read-only diagnostic:

```text
./setup.sh --verify-server
```

On Windows use `./setup.ps1 -VerifyServer`. The setup creates a managed Python environment inside the installed Skill. On macOS/Linux, prefer `scripts/run_from_image.sh`; on Windows, use `scripts/run_from_image.ps1`. Do not rely on packages installed into the operating-system Python.

The default private route uses SSH target `supersvg-server` and runs SuperSVG inside `services/supersvg-eval` relative to the remote home directory. Override both values through explicit script arguments. No external API key or usage credit is required.

SuperSVG deployment changes the remote server and must only run when the user explicitly asks to deploy or refresh it. Read [references/server-runtime.md](references/server-runtime.md), then use `scripts/deploy_supersvg.py`. Prefer `--mode adapters` for an existing runtime; use `--mode bootstrap` only for a new or incomplete runtime. A deployment is not complete until `--mode verify` passes, and a real smoke image is recommended before a full figure.

Before an authorized SuperSVG job, follow the GPU1 handoff in [references/server-runtime.md](references/server-runtime.md). Preserve the pre-run state of the independent SAM3 service on GPU0; start it only when optional complex-asset foreground contours are needed, then restore that original state.

## Input preparation and object routing

1. Preserve the untouched PNG, JPEG, or WebP.
2. Record every visible text run in a schema `1.0` text manifest: content, x/y, bbox, font family, font size, weight/style, fill, opacity, rotation, alignment, z-index, and paint order.
3. Build a schema `1.0` Scene Manifest with stable ids, normalized bounding boxes, draw order, styles, and explicit object types.
4. Route `background`, `region`, `frame`, `rect`, `rounded_rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `arrow`, `connector`, `axis`, `heatmap`, and `gradient_legend` to direct native construction.
5. Route only `semantic_asset`, `asset`, and `subject` crops to private SuperSVG. Tight crops must exclude nearby text, arrows, frames, and connectors. Preserve the full crop resolution and use `optimize_iter >= 10`; choose enough paths for the asset's detail instead of imposing a speed cap.
6. Restore text as live `<text>` elements from the text manifest. Do not ask SuperSVG to synthesize or preserve text.

Read [references/manifest-schema.md](references/manifest-schema.md) when creating or repairing either manifest.

## Run the portable pipeline

Use `scripts/run_from_image.py` as the single entrypoint. It accepts the original reference, Scene Manifest, text manifest, and output root. If complex assets are unresolved it crops and vectorizes only those assets in one SuperSVG model load; if they are already resolved it validates and reuses them. The script:

- creates an atomic `illustrator-flowchart-N` job directory;
- validates the object split and resolves only the declared complex assets through SuperSVG;
- composes direct native elements with validated complex-asset SVGs in exact draw order;
- rejects invalid XML, empty vectors, raster `<image>`, scripts, and unsupported external content;
- restores live text and validates the Master SVG again;
- creates an immutable geometry cache only when it can represent every source feature without loss;
- routes the final step by platform.

Platform behavior:

- **Windows:** use the retained PowerShell/COM bridge for Illustrator 2026.
- **macOS:** use the Python AppleScript/JSX bridge; Illustrator and the target document must already be open. Checkpoint less often to reduce overhead, but never change the geometry.
- **Linux:** complete through validated Master SVG and geometry cache; do not claim Illustrator output because Illustrator is unavailable.

Use `--scene-manifest /absolute/path/scene.json` for every run. Use `--no-illustrator` when the user wants SVG only. Use `--dry-run` for a cache-only verification. Use `--sam3-foreground-clips` only when the manifest contains appropriate SAM3 prompts/boxes and the independent service is available.

## Scientific and text correctness

- Treat extracted text, numeric values, chemical labels, gene names, axis labels, and legends as authoritative.
- Remove those regions before SuperSVG when possible, then restore them as live text after vector generation.
- Do not accept high visual similarity as proof of scientific correctness.
- For scientific figures, compare the final rendering with the untouched reference and explicitly inspect labels, arrows, axes, legends, and directionality.
- Missing fonts, text overflow, altered chemical atoms, changed numbers, or a rule element accidentally baked into a complex asset are blockers until corrected or explicitly accepted by the user.

## Illustrator behavior

- Require the user to open Illustrator and the target document. Do not launch, quit, focus, resize, or move the application window.
- Append only inside the named Illustrator流程图绘制 job group; do not delete, hide, rename, or move existing artwork.
- Reuse cached atoms and stable names so retries skip completed objects.
- Ordinary batches contain 20–50 consecutive atoms; only genuinely complex atoms may be singletons.
- Save periodic checkpoints and export PNG only after structural QA passes. Checkpoint frequency is a performance control and must not affect path content.
- Arbitrary vector `userSpaceOnUse` clip contours, including optional SAM3 foreground contours, are retained as native Illustrator clipping paths. Solid fills, linear gradients, dash arrays, strokes, and live text are native. If radial gradients, masks, filters, patterns, or another feature cannot be represented losslessly, stop at the validated Master SVG. Do not normalize the feature away and do not claim Illustrator completion.

## Completion gate

Do not report success until the applicable outputs pass:

- the Scene Manifest explicitly separates direct rule elements from complex semantic assets;
- every complex-asset SuperSVG quality job completed and its id/state were saved;
- direct text/lines/arrows/frames/basic shapes were not sent through SuperSVG;
- every asset SVG and the composed hybrid SVG are valid, editable, non-empty, and contain no embedded raster;
- Master SVG contains restored live text and passes the same validator;
- geometry cache matches the Master SVG hash and batch rules;
- cached atom/paint-part counts and supported presentation features match the Master SVG; no optimization may reduce them;
- on macOS/Windows, Illustrator output contains every expected atom and no placed/raster items;
- on macOS/Windows, the exported PNG passes render-equivalence QA against the validated Master SVG;
- on Linux or SVG-only mode, clearly state that AI/PNG playback was not performed;
- final output was visually checked against the untouched reference when scientific correctness matters.

Return the Master SVG and validation-relevant deliverables. Include AI and PNG only when Illustrator playback actually completed.
