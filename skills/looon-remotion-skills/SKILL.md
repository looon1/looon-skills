---
name: looon-remotion-skills
description: Create and customize Remotion explainer videos in the Looon visual style with paper or image backgrounds, bold cards, hard shadows, animated connectors, subtitles, and optional presenter video. Use when Codex is asked to make a Remotion information-flow animation, reuse the Looon/Cowart example, replace a background image, change brand colors, or render a configurable short-form explainer.
---

# Looon Remotion

Create a new project from the bundled template, customize its theme, then render and inspect the result.

## Workflow

1. Inspect the requested background image before using it. Record whether it is landscape, portrait, transparent, busy, or low contrast.
2. Create a project with `scripts/create_project.py`. Never overwrite an existing destination.
3. Edit `src/theme.json` for colors and background behavior. Read [references/theme-schema.md](references/theme-schema.md) when adding fields.
4. Edit scene copy, nodes, and timings in `src/compositions/CowartFlow.tsx`.
5. Run `npm install`, `npx tsc --noEmit`, and `npm run render`.
6. Generate a still with `npm run still` and visually inspect it before reporting completion.
7. Use `npm run studio` only when interactive timeline tuning is useful. Studio is optional for CLI rendering.

## Create a project

```bash
python3 scripts/create_project.py \
  --output /absolute/path/to/project \
  --background-image /absolute/path/to/background.png \
  --background-color '#fffaf0' \
  --accent-color '#f6bc35' \
  --ink-color '#17140f'
```

Omit `--background-image` to use the built-in grid-paper background. Use `--background-mode solid` for a plain background.

## Required visual behavior

- Keep the composition data-driven and deterministic.
- Animate with `useCurrentFrame()`, `spring()`, and `interpolate()`; never use CSS transitions.
- Use 1920×1080 at 30fps unless the user requests another format.
- Preserve thick outlines, offset hard shadows, restrained colors, and staged connector growth.
- Maintain readable contrast when a background image is supplied. Raise `background.overlayOpacity` when needed.
- Treat the presenter layer as optional. Do not invent a real person asset.
- Do not commit `node_modules/` or rendered working files unless the user explicitly requests example outputs.

## Bundled resources

- `assets/template/`: reusable Remotion project.
- `assets/template/public/background-grid.svg`: default background asset.
- `assets/example-output/`: verified MP4 and still from the reference implementation.
- `references/theme-schema.md`: supported theme fields.
