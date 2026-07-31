# Theme schema

Edit `src/theme.json`.

| Field | Purpose |
|---|---|
| `background.mode` | `grid`, `image`, or `solid` |
| `background.color` | Base canvas color |
| `background.image` | File name inside `public/`, or `null` |
| `background.fit` | CSS background size such as `cover` or `contain` |
| `background.position` | CSS background position |
| `background.overlayOpacity` | Paper-colored overlay from `0` to `1` |
| `background.gridSize` | Grid spacing in pixels |
| `background.motion.enabled` | Enable deterministic background movement |
| `background.motion.direction` | `left-to-right` or `right-to-left` |
| `background.motion.distance` | Total horizontal travel in pixels |
| `background.motion.scale` | Background overscan scale; keep at least `1.02` |
| `palette.paper` | Card and light text color |
| `palette.ink` | Outline, title, and dark card color |
| `palette.accent` | Connector and badge color |
| `palette.shadow` | Secondary hard-shadow color |

For a visually busy image, use `overlayOpacity` between `0.45` and `0.75`. For a subtle texture, use `0.15` to `0.35`.

The default movement is 120 pixels over the whole composition. For a 10-second
video, use 80–140 pixels. For a 30–60 second video, use 160–280 pixels. Keep the
movement slow enough that it reads as ambient motion rather than a camera pan.
