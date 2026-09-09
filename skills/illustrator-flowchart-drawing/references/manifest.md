# 文字与插画清单

JSON 清单由查看原图的 agent 编写。OCR 只能帮助提取，必须逐字核对。
所有 `bounds` 都用原始图片左上角为原点的像素坐标 `[left, top, right, bottom]`，右、下边界不包含在内。每条 label 对应一行文字的**实际墨迹边框**，不是包含大块空白的选区。

```json
{
  "labels": [
    {
      "text": "Result ≥ 20",
      "bounds": [80, 35, 260, 65],
      "font": "ArialMT"
    }
  ],
  "groups": [
    {
      "name": "Sample illustration",
      "bounds": [70, 100, 210, 260]
    }
  ]
}
```

这些坐标只是格式示例，不是任何用户图片的重建参数。

- `font` 是 Illustrator `app.textFonts` 中的 PostScript 名称。字体不存在时先选择经检查的替代字体并更新清单。
- label 可选 `background` 为 `[r,g,b]`，指定背景补片色。未提供时，准备程序从原生描摹预览的文字边框周围排除深色墨迹后选取出现次数最多的浅色。这个规则仅适用于深色文字、浅色纯色背景；必须看实际色块。
- label 可选 `color` 为文字 RGB，默认 `[20,20,20]`。
- 可选 `padding` 设置修补区外扩像素（0–10，默认 3）；紧密结构式字母需要根据实际间距缩小。边框必须避开附近箭头、描边和其他文字，否则自动删除会伤及插画。程序拒绝越界或互相重叠的文字修补区。
- 插画区域不要彼此相交。可以包含需恢复的插画内标签；标签先单独修复，再将剩余插画路径分组，文字始终位于独立的可编辑文字层。
- `repair: "glyphs"` 仅修补边框内深色字形路径：用背景色填回旧字形，再创建活文字，保留周围纹理。这是标签位于有纹理插画内部时的局部修补选择，不能重建被文字挡住的真实纹理；必须放大查看旧字形边缘。默认 `rectangle` 仅适合纯色背景。两种方式均需确保修补区域没有其他深色图形。
- 必须逐字登记全部可辨认文字，不能因为文字位于插画内部就留作路径。先核对字体是否真的含有该字形。下标字体缺字时，可以把正常数字作为单独原生文本对象，按原图的字号与下标位置排版；不能接受缺字框。
- 若两次准备指向同一个 job，输入像素必须一致；换图片时使用新 job。改变标签后重建应使用新的输出目录，避免覆盖已审核的成品。

原图尺寸为 `W×H`、屏幕显示为 `w×h` 时，先换算 `x_source=x_screen*W/w`、`y_source=y_screen*H/h`。需要进一步查找墨迹边界时可以用 Pillow 分析局部深色像素，但不要把阈值分割结果未经观察直接认定为文字。

## 原生几何与复杂插画分离

在完整文字/插画清单中加入 `nativeLayout`。`rebuild` 会在文字与插画分组后应用该布局。复杂插画以外的原描摹层会被移除，因此应先核对所有插画、血管、装饰和小符号是否已被保留或用原生对象替代。

```json
{
  "nativeLayout": {
    "elements": [
      {"name":"Panel frame","type":"rect","bounds":[20,20,500,300],"stroke":[190,55,45],"width":4},
      {"name":"Dashed callout","type":"path","points":[[[10,50]],[[200,150]]],"stroke":[40,40,40],"width":2,"dashes":[5,4]},
      {"name":"Arrow","type":"path","points":[[[230,150]],[[360,150]]],"stroke":[40,40,40],"width":2,"arrow":[12,10]}
    ],
    "regions": [],
    "removeTraced": []
  }
}
```

以上坐标仅说明格式。原生元素名称必须唯一。

- `rect`、`ellipse` 使用与文字相同的图片坐标 `bounds`。`fill` 为 RGB，缺省或 `null` 表示无填色；`stroke` 为描边 RGB，`width` 为描边宽度。`background:true` 放入底层，其余元素放入前景原生几何层。
- `path.points` 中每项是 `[[anchorX,anchorY]]`，或 `[[anchorX,anchorY],[leftHandleX,leftHandleY],[rightHandleX,rightHandleY]]`。锚点与控制柄均采用图片左上角坐标。`closed:true` 创建闭合路径。
- `dashes` 是交替的实线段/空隙长度，全部为正数；虚线保持为一条有描边的路径，不拆成单独短线。`arrow:[length,width]` 创建由曲线和三角形头部组成的原生分组。
- 线性渐变填色可写为 `{"stops":[[0,[255,255,255]],[100,[255,190,190]]],"origin":[20,300],"length":280,"angle":-90}`。仅 `origin` 使用 Illustrator 的左下角坐标；`angle` 通过只旋转填色渐变的原生路径操作应用，路径几何不旋转。
- `regions` 可以从原描摹层剩余对象中补充复杂插画组，例如前景细胞分组后剩余的血管。每项为 `{"name":"Vessel","bounds":[...]}`；按清单顺序分配已完整落入区域的对象，前面组已拿走的对象不会重复。跨越区域的轮廓不会自动裁切，需要调整区域或单独处理。
- `removeTraced` 仅用于已经混入复杂插画组的旧虚线碎片等，格式为 `{"group":"Exact illustration group","bounds":[...],"maxGray":110}`。它只移除指定区域内近中性的深色填充路径；必须先检查颜色、范围及预览，不能大范围套用而误删插画轮廓。

已有可编辑 AI 时，在新的任务与输出目录运行：

```bash
python scripts/prepare_job.py /absolute/reference.png \
  --job-dir /absolute/new-job --output-dir /absolute/new-output \
  --manifest /absolute/full-manifest.json --editable-source /absolute/verified-figure.ai
python scripts/run-illustrator-mac.py --job-dir /absolute/new-job --stage structure
python scripts/run-illustrator-mac.py --job-dir /absolute/new-job --stage verify
python scripts/run-illustrator-mac.py --job-dir /absolute/new-job --stage live
```

`--editable-source` 会复制源 AI 到任务目录的 `source.ai`，不会写回原文件。`structure` 接受本 Skill 生成、尚未应用 `nativeLayout` 的可编辑 AI，须保留原有的 `01 Panels and connectors`、`02 Illustrations`、`03 Text background repairs` 等图层。它保留已有文本，不重新修补文字；已核验文本之间的补片范围重叠不阻止此阶段。文字清单仍须与该 AI 完全匹配，显式填写 `background` 可省去读取描摹预览。Windows 对应使用 PowerShell 启动器的 `-Stage structure`、`verify`、`live`。
