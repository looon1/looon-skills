# Manifest schema 1.0

## Scene Manifest

Required root fields:

```json
{
  "schema_version": "1.0",
  "canvas_size": {"width": 1327, "height": 1185},
  "objects": []
}
```

Every object requires a stable `id`, unique integer `draw_order`, supported `type`, and geometry. Coordinates are normalized by default; set `"coordinate_space": "absolute"` for canvas units.

Direct types:

- `background`, `region`, `frame`, `rect`, `rounded_rect`
- `circle`, `ellipse`, `polygon`
- `line`, `polyline`, `connector`, `axis`, `arrow`
- `heatmap`, `gradient_legend`

Rectangular objects use `bbox` or `bbox_normalized` with `x`, `y`, `width`, and `height`. Lines/connectors/arrows use `points` or `x1/y1/x2/y2`. Visual attributes belong in `style`; arrows may also set `head_length` and `head_width`. A `gradient` contains `type`, coordinates, and at least two `{offset, color, opacity?}` stops.

Complex types are only `semantic_asset`, `asset`, and `subject`. They require a bbox and may contain:

- `crop_padding_px`
- `background_policy`: `transparent` by default, or `preserve` only when the background belongs to the semantic object
- optional `background_tolerance`, `background_feather`, `matte_vector_tolerance`, `matte_neutral_luminance`, and `matte_neutral_chroma`
- `vector_profile`: `rows`, `cols`, `overlap`, `path_num`, `optimize_iter`, `refine_batch_size`
- `clip_to_bbox`
- optional `sam3_prompts`, `sam3_boxes`, `sam3_prompt_limits`, and `segmentation_optional`

Before vectorization, `asset_svg`, `source`, `status`, and `vector_valid` may be absent. The pipeline resolves them. After resolution, `source.provider` must equal `supersvg`.

When the ChatGPT web client is used before SuperSVG, the semantic object may also contain `source_enhancement` with `provider: chatgpt-web-imagegen`, `mode: web`, `client: leeguooooo/chatgpt-imagegen`, client version, source crop, generated transparent PNG, prompt record, transparency result, semantic audit decision, and optional audit notes. `generated_png` may be absolute or relative to the manifest. Only `semantic_audit: accepted` with a readable, genuinely transparent RGBA PNG may override the original crop as SuperSVG input. This records intermediate provenance only; the final provider remains private SuperSVG and the generated PNG must not appear in the Master SVG.

Panel fills must be separate direct objects placed earlier in `draw_order`. A resolved transparent asset also records `asset_source_crop`, `asset_crop`, `background_removal`, `background_transparent`, and a matte-removal report beside its SVG. Never encode a panel's pale blue/green/gray field inside multiple semantic assets.

## Text Manifest

```json
{
  "schema_version": "1.0",
  "text_elements": [
    {
      "id": "title",
      "content": "Editable title",
      "x": 0.5,
      "y": 0.08,
      "coordinate_space": "normalized",
      "font_family": "Arial",
      "font_size": 32,
      "font_weight": "bold",
      "fill": "#000000",
      "text_anchor": "middle",
      "paint_order": 100
    }
  ]
}
```

Every text element requires `id`, `content`, `x`, and `y`. Optional fields include font family/size/weight/style, fill, opacity, rotation, line height, anchor, baseline, z-index, and paint order. Newlines remain separate editable Illustrator text frames.
