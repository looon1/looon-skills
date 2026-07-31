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
| `palette.paper` | Card and light text color |
| `palette.ink` | Outline, title, and dark card color |
| `palette.accent` | Connector and badge color |
| `palette.shadow` | Secondary hard-shadow color |

For a visually busy image, use `overlayOpacity` between `0.45` and `0.75`. For a subtle texture, use `0.15` to `0.35`.
