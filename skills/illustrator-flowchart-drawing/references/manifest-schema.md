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
- `vector_profile`: `rows`, `cols`, `overlap`, `path_num`, `optimize_iter`, `refine_batch_size`
- `clip_to_bbox`
- optional `sam3_prompts`, `sam3_boxes`, `sam3_prompt_limits`, and `segmentation_optional`

Before vectorization, `asset_svg`, `source`, `status`, and `vector_valid` may be absent. The pipeline resolves them. After resolution, `source.provider` must equal `supersvg`.

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
