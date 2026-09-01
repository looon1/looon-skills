# Illustrator流程图绘制 SuperSVG replacement audit

Audit date: 2026-09-01

Package version: `1.0.0`

Overall result: `PASS_WITH_ENVIRONMENT_LIMITATIONS`

## Architecture decision

The corrected pipeline is object-routed, not whole-frame model tracing:

1. A required Scene Manifest classifies every visible object.
2. Text, lines, arrows, connectors, frames, regions, axes, circles, ellipses, rectangles, polygons, gradients, and other rule elements are constructed directly as native SVG objects.
3. Only complex semantic crops such as animals, cells, textured proteins, organelles, molecular illustrations, and irregular scientific icons are sent to the private `JTUplayer/SuperSVG` runtime.
4. The validated complex-asset SVGs are composed with the direct objects in original paint order.
5. Text is restored as live SVG text from the text manifest.
6. The Master SVG is validated, converted into an immutable lossless geometry cache, and optionally replayed into Illustrator on macOS or Windows.

SAM3 remains optional foreground segmentation for complex-asset clipping only. It is not a vector model. The package contains no executable or configuration path to a legacy vector provider.

## Quality controls

- Whole-frame SuperSVG input is rejected by design because a Scene Manifest is mandatory.
- Rule elements cannot declare a SuperSVG asset source.
- SuperSVG quality mode rejects fewer than 1,000 paths per crop/tile or fewer than 10 refinement iterations; defaults are 1,600 paths and 14 iterations.
- Multiple complex assets are processed in one model load by default. This improves throughput without reducing path count or refinement.
- SVG validation rejects raster images, scripts, invalid XML, empty vectors, unsupported external content, missing stable ids, and unresolved semantic assets.
- The cache preserves path geometry, paint parts, native linear gradients, dash arrays, live text, and arbitrary vector clipping paths supported by the Illustrator adapter.
- Unsupported lossless Illustrator features stop at the validated Master SVG instead of being flattened or silently removed.

## Test evidence

| Check | Result | Evidence |
|---|---|---|
| Python compilation | PASS | All package Python files and both server adapters compiled successfully. |
| Shell syntax | PASS | macOS/Linux setup and run wrappers passed shell syntax validation. |
| Skill package validation | PASS | Skill metadata and required structure passed the Codex skill validator. |
| Local dependency doctor | PASS | Managed Python, Pillow, fontTools, SSH/SCP, package files, and optional ImageMagick were detected. |
| SuperSVG deployment planner | PASS | Verify, adapter-refresh, and pinned bootstrap modes completed dry-run command audits without contacting or mutating a server. |
| Public-package privacy scan | PASS | Private host aliases, IP addresses, personal remote paths, credentials, and local absolute paths were removed from executable source and documentation. |
| Offline integration fixture | PASS | Direct gradient, dashed rule, arrow, live text, resolved complex asset, disconnected clip, cache schema 5, and zero raster nodes; 6 atoms in 3 batches. |
| Wrong-render rejection | PASS | A stale PNG produced normalized RMSE `0.608953` and was rejected against the `0.055` threshold. |
| Same-source render control | PASS | A same-source fixture produced normalized RMSE `0.0`. |
| Real figure object routing | PASS | 54 scene objects: 17 complex SuperSVG assets and 37 direct native objects; no whole-frame model input. |
| Real private SuperSVG job | PASS | Provider `supersvg`, model `JTUplayer/SuperSVG`, 17 assets, 1,600 paths per asset, 14 refinement iterations, completed job state recorded. |
| Real Master SVG validation | PASS | 27,330 vector elements, 45 live text elements, 0 raster nodes, strict ids, no errors or warnings. |
| Real Illustrator cache/playback | PASS | Cache schema 5, 18,925 atoms, 392 of 392 batches completed, no recorded playback errors. |
| Real Illustrator document | PASS | 19,266 path items, 45 text frames, 0 placed items, 0 raster items; AI and PNG exports exist. |
| Executable-source/provider/security scan | PASS | No legacy vector-provider route, API key, bearer token, or embedded local-user path was found in executable source or configuration. |
| Renamed full-pipeline regression | PASS | `illustrator-flowchart-1` regenerated the 27,330-element Master SVG and schema-5 cache with 18,925 atoms in 392 batches and 0 raster nodes. |

## Environment limitations

- The private SSH endpoint refused the final online diagnostic during this publication audit. The earlier real 17-asset SuperSVG job completed and its state is retained, but the current server state was not re-certified. Run `scripts/deploy_supersvg.py --mode adapters` and a smoke image when the endpoint is reachable.
- The Windows PowerShell/COM path was reviewed and packaged but was not executed on a Windows host during this audit.
- The Linux core path is platform-neutral Python and completes through Master SVG plus cache, but this audit executed the SVG-only path on macOS rather than a separate Linux host. Illustrator output is intentionally unavailable on Linux.
- The full 16 MB Master SVG render-equivalence comparison was not rerun because the local ImageMagick SVG renderer exceeded the practical audit window. Small-fixture positive and negative render gates passed, and the full real artifact passed structural validation, cached playback, Illustrator object inspection, and visual export inspection.

## Installation and run

macOS/Linux:

```bash
./setup.sh --verify-server
./scripts/run_from_image.sh \
  --input-image /absolute/path/reference.png \
  --scene-manifest /absolute/path/scene.json \
  --text-manifest /absolute/path/text-manifest.json \
  --output-root /absolute/path/output
```

Windows:

```powershell
./setup.ps1 -VerifyServer
./scripts/run_from_image.ps1 \
  -InputImage C:\path\reference.png \
  -SceneManifest C:\path\scene.json \
  -TextManifest C:\path\text-manifest.json \
  -OutputRoot C:\path\output
```

Use `--no-illustrator` on macOS/Linux or `-NoIllustrator` on Windows for validated SVG and cache only.
