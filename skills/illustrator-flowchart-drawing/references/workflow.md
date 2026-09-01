# Illustrator流程图绘制 SuperSVG workflow

## Required inputs

- Untouched reference PNG, JPEG, or WebP.
- Scene Manifest schema `1.0`, separating direct rule elements from complex semantic assets.
- Text manifest schema `1.0`, containing `text_elements`.
- Output root.

The Scene Manifest may be unresolved. The entrypoint detects missing complex-asset SVGs, crops only those objects, submits them to private SuperSVG in one model load, validates the results, and writes a resolved manifest inside the job directory.

## One command

macOS/Linux:

```bash
./scripts/run_from_image.sh \
  --input-image /absolute/path/reference.png \
  --scene-manifest /absolute/path/scene.json \
  --text-manifest /absolute/path/text-manifest.json \
  --output-root /absolute/path/output
```

Windows:

```powershell
./scripts/run_from_image.ps1 \
  -InputImage C:\path\reference.png \
  -SceneManifest C:\path\scene.json \
  -TextManifest C:\path\text-manifest.json \
  -OutputRoot C:\path\output
```

Useful options:

- `--supersvg-path-num 1600`: paths per complex crop/tile; minimum 1,000.
- `--supersvg-optimize-iter 14`: refinement iterations; minimum 10.
- `--supersvg-rows` and `--supersvg-cols`: increase only for dense complex crops that need tiled detail.
- `--sam3-foreground-clips`: optional foreground contours after SuperSVG crops exist.
- `--force-vectorize-assets`: regenerate already-resolved complex assets.
- `--no-illustrator`: validated Master SVG and cache only.
- `--dry-run`: build and audit the immutable cache without changing Illustrator.

There is no whole-frame mode and no alternate vector provider.

## Outputs

Each run reserves `illustrator-flowchart-N/` and writes:

- `assets/`: complex-asset crops, validated SuperSVG files, and remote job state.
- `illustrator-flowchart-N-scene-resolved.json`: emitted when unresolved assets were vectorized.
- `illustrator-flowchart-N-scene-segmented.json`: emitted only when optional SAM3 contours were requested.
- `illustrator-flowchart-N-hybrid-base.svg`: direct rule elements plus complex SuperSVG assets.
- `illustrator-flowchart-N.svg`: validated Master SVG with live text.
- `.illustrator-flowchart-internal/live-cache/geometry-cache.json`: immutable parsed geometry.
- `.illustrator-flowchart-internal/live-cache/playback.json`: resumable playback progress.
- `illustrator-flowchart-N.ai` and `illustrator-flowchart-N.png`: only after Illustrator playback and QA.

## Platform boundary

- macOS: complete pipeline plus AppleScript/JSX Illustrator playback.
- Windows: complete pipeline plus PowerShell/COM Illustrator playback.
- Linux: complete through Master SVG and geometry cache; Illustrator output is not claimed.

## Quality invariant

Rule elements never enter SuperSVG. Performance changes may alter only submission, tiling, batching, retry, caching, and checkpoint frequency. They must not lower the quality floor, simplify paths, remove paint parts, flatten gradients, remove clipping, reduce accepted crop resolution, or change stacking. If the Illustrator adapter cannot represent a validated SVG feature losslessly, return the Master SVG and report the unsupported feature.
