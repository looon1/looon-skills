# Illustrator runtime by platform

The portable core always creates a validated Master SVG and geometry cache. Illustrator playback is an optional final adapter.

## Windows

`run_illustrator_flowchart.py` delegates to the retained `run_illustrator_flowchart.ps1` bridge, which:

- verifies Illustrator is already running;
- opens one `Illustrator.Application.30` COM proxy;
- reuses the immutable cache and named batch groups;
- checkpoints AI output and performs structural QA;
- exports the final PNG once.

This remains the retained Windows Illustrator implementation route. Validate it on the target Windows/Illustrator version before claiming a completed Windows playback.

## macOS

`run_illustrator_flowchart.py` verifies an Illustrator process already exists, then uses `osascript` to ask Illustrator to execute temporary JSX bootstrap files. The same `illustrator_flowchart_cached_runtime.jsx` creates native paths and live text.

The bridge does not intentionally activate, launch, resize, or close Illustrator. macOS requires Automation permission for the terminal/Codex host to control Adobe Illustrator. Test with a disposable open document before using a valuable document. It may checkpoint after multiple completed batches to avoid repeated save overhead; this does not change, combine, simplify, or omit any atom.

## Linux

Adobe Illustrator is unavailable. The runner automatically reports `core-only` and stops after Master SVG, geometry cache, and playback state. Do not claim AI or PNG output.

## Supported SVG subset

The cache accepts path, rect, circle, ellipse, line, polyline, polygon, live text, solid fills/strokes, linear gradients, dash arrays, opacity, transforms, and arbitrary vector `userSpaceOnUse` clip contours. Disconnected clip contours are joined with retraced zero-area bridges and even-odd fill so Illustrator receives one native clipping PathItem without changing the visible region.

It rejects raster images, `<use>`, object-bounding-box clips, nested non-redundant curved clips, masks, filters, radial gradients, patterns, scripts, foreign objects, class-dependent CSS, linked resources, and unsupported effects. Rejection is a quality boundary: never strip an unsupported feature to force playback. Preserve and return the validated Master SVG until a lossless adapter is available.

## Recovery

Stable job, batch, and atom names make playback idempotent. `playback.json` records attempts and completion. On failure, preserve the Master SVG, geometry cache, and playback file; rerun with the same job directory instead of generating a new SVG.
