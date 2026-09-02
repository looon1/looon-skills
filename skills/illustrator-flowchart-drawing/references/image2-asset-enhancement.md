# ChatGPT web image generation for complex-asset enhancement

Use this optional route only when a complex semantic crop is too small, noisy, background-contaminated, or visually degraded by direct SuperSVG reconstruction. Do not apply it to text, arrows, connectors, panels, axes, chemical labels, exact molecular structures, or the whole reference image.

## Selected public client

Use [`leeguooooo/chatgpt-imagegen`](https://github.com/leeguooooo/chatgpt-imagegen), pinned to the installed and audited client version, with `--backend web`. This route drives the user's already signed-in ChatGPT website through `chrome-use`, but the flowchart agent calls one local command rather than manually operating browser elements. It uses neither the Codex built-in image generator nor `OPENAI_API_KEY`.

The upstream project currently warns that subscription image generation does not guarantee native transparency. Treat web transparency as a capability to verify, never as an assumption. This Skill's wrapper rejects any downloaded result without a real non-opaque alpha channel, including painted checkerboards.

## Required setup

- `chatgpt-imagegen` installed locally. The verified public version during integration was `0.23.6`.
- `chrome-use` installed with its extension connected to Chrome.
- The selected Chrome profile is already signed in to `chatgpt.com`.
- Run `./setup.sh --verify-chatgpt-web` before the first job or after a browser/client update.

Installing or changing the browser bridge is a separate machine-level action. Do it only when the user explicitly authorizes that setup.

1. Keep the untouched reference and exact source crop.
2. Treat the crop as the sole subject reference. Run `scripts/chatgpt_web_image_asset.py` once per distinct complex asset; the wrapper forces `--backend web` and never uses automatic fallback.
3. Ask for one isolated foreground object on a genuinely transparent canvas at the highest practical resolution. Preserve the downloaded bytes and generated alpha channel.
4. Save the output and wrapper report inside the current job's `assets/enhanced/` directory. Do not overwrite an existing file.
5. The wrapper rejects missing files, non-PNG data, no alpha channel, fully opaque alpha, fully transparent output, and failed client runs. A rejected file remains an audit artifact and must not enter the manifest as accepted.
6. Separately reject the generated asset if it changes scientific structure, adds/removes parts, changes directionality or count, introduces pseudo-text, or contains a colored canvas/checkerboard within visible pixels.
7. Route only an alpha-passing and semantically accepted PNG through private SuperSVG, its SVG validator, and matte/foreground cleanup. Compose it above one native panel background layer.

If the web backend is unavailable, report whether `chatgpt-imagegen`, `chrome-use`, extension connectivity, or ChatGPT login is missing. Do not use `--backend auto`, because it can silently spend the Codex image bucket. Continue with the untouched crop and direct SuperSVG only when it can still meet the quality gate.

## Wrapper command

```bash
./scripts/chatgpt_web_image_asset.py \
  --reference /absolute/path/object-source.png \
  --prompt "<normalized prompt contract below>" \
  --output /absolute/path/job/assets/enhanced/object-web.png \
  --report /absolute/path/job/assets/enhanced/object-web.json
```

The wrapper pins `--backend web`, disables style injection and client self-update for the run, downloads PNG, and verifies the actual alpha extrema. Exit code `0` means alpha passed but semantic review is still pending; exit code `1` means the web client failed; exit code `2` means a file was downloaded but transparency failed.

## Suggested prompt contract

Use case: `background-extraction` when the source quality is adequate and only the background is defective; otherwise use `precise-object-edit` for a faithful clean reconstruction.

State the object name and label the crop as `Image 1: edit target`. Request a faithful high-resolution reconstruction, genuine transparent RGBA background, no canvas color, no text, no symbols, no arrows, no frame, no extra objects, and no semantic redesign. Repeat the invariants in every iteration. For biological objects, require the same visible morphology, component count, relationships, and orientation without adding anatomical detail not shown in the source.

Example prompt skeleton:

```text
Use case: precise-object-edit
Asset type: isolated scientific-figure foreground asset for later vectorization
Primary request: faithfully reconstruct only <object name> from Image 1 as a clean high-resolution scientific illustration
Input images: Image 1: edit target and sole visual reference
Style/medium: preserve the original flat scientific-illustration style, palette, shading, and line weight
Composition/framing: one centered object with the same pose, orientation, silhouette, component count, and internal relationships
Scene/backdrop: genuinely transparent RGBA canvas
Constraints: change only edge cleanliness and resolution; preserve scientific identity; no text, labels, arrows, symbols, frames, panel colors, shadows outside the silhouette, extra objects, or invented anatomy
Avoid: pseudo-text, white or colored background, halo, crop, semantic redesign, watermark
```

## Audit fields

Record these under the semantic object when this route is used:

- `source_enhancement.provider`: `chatgpt-web-imagegen`
- `source_enhancement.mode`: `web`
- `source_enhancement.client`: `leeguooooo/chatgpt-imagegen`
- `source_enhancement.client_version`
- `source_enhancement.source_crop`
- `source_enhancement.generated_png`
- `source_enhancement.prompt_record`
- `source_enhancement.transparent_rgba`: `true`
- `source_enhancement.semantic_audit`: `accepted` or `rejected`
- `source_enhancement.audit_notes`

The generated PNG is an intermediate source asset. It must not be embedded as a raster node in the final Master SVG or Illustrator document.
