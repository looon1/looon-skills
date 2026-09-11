# PowerPoint 实时绘制

用户指定 PowerPoint 时走本分支，保留 Illustrator 分支供 AI 输出。PowerPoint 目标是原生文本、几何、渐变、箭头和可核验的 `.pptx`。不要把离线生成后打开、动画揭示或整页截图称为实时绘制。

## 选择实际可用的接口

- Windows：先调用 `powerpoint_status`、`powerpoint_get_capabilities` 和 `powerpoint_inspect`。有 Scientific Illustrator MCP 时用其原生接口，创建独立演示文稿，并按区域做结构审计及 PowerPoint 渲染检查。该 COM 接口不能用于 macOS。
- macOS：本 Skill 自带 `prepare_powerpoint.py` 和 `run-powerpoint-mac.py`。使用已打开的桌面 PowerPoint，通过 AppleScript 原生对象模型逐对象创建。先前台查看空白目标页，再单步、暂停、继续。不要以 Windows 插件报错推断 Mac 无法操作。
- 其他平台：可以准备文件，但不宣称实时绘制已完成。

Mac 原生字典没有与 COM `BuildFreeform` 对等的公开入口。因此先把显式几何编译为一个内部 PPTX 缓存，再用 `copy shape` 与 `paste object view of active window` 将对象逐个复制到同一任务的空白目标页。复制后回设原始位置与尺寸，避免连续粘贴偏移。这是缓存几何的原生对象播放，不能称为模拟人类逐笔绘画。源缓存页留作内部工作，完成时只删除本任务会话的源页。现有用户演示文稿不修改、不关闭。

## 内容与编辑性

先根据参考图建立完整清单，记录原图尺寸、全部文字、对象 id、范围和前后顺序。文字、简单背景、边框、曲线、直线、虚线、箭头及可准确重建的结构使用原生几何。原生自由曲线保存为 DrawingML 贝塞尔曲线，不转成像素或大量短线。

复杂插画有两种明确模式：

- `native`（默认）：不允许图片。只有实际重建或导入并验证为原生自由曲线的复杂对象才能计入完成。不要把 SVG 图片当作原生自由曲线。
- `hybrid`：保留单个复杂插画的紧裁 PNG，交付时明确列出图片数量和不能编辑的内部内容。这是混合编辑方案，不能沿用 Illustrator 分支的“零位图”验收结论。用户要求全部矢量时不可用它冒充完成。

从原图提取的插画不得带入文字、边框或连接器；若发现残留，应处理并重新核对，或在报告中标为未解决。重复元素和可几何重建的结构不因为方便而合并成截图。覆盖住旧字不代表源图片中已移除旧字。

## Mac 清单与命令

清单使用参考图像素坐标，编译时等比映射为 10 英寸宽的自定义比例幻灯片。文本字号也使用同一坐标单位。

```json
{
  "schema": 1, "width": 1000, "height": 700, "mode": "native",
  "objects": [
    {"id":"panel", "type":"rect", "bounds":[20,20,960,660], "fill":["FFFFFF","EAF4FA"], "stroke":"2875A0", "stroke_width":2},
    {"id":"label", "type":"text", "bounds":[60,60,320,40], "text":"Activation", "font_size":28, "color":"111111"},
    {"id":"arrow", "type":"path", "bounds":[90,150,150,80], "commands":[["M",90,150],["C",130,150,180,230,240,230]], "stroke":"303535", "stroke_width":3, "arrow":true}
  ]
}
```

支持 `rect`、`ellipse`、`text`、`path`、`image` 及复杂对象章节说明的原生 `group`。路径命令是绝对坐标 `M/L/C/Q/Z`；`bounds` 必须容纳整条曲线。颜色为六位 RGB；`fill` 可为空、纯色或垂直渐变色列表。文本默认 Arial，保留 Unicode，可指定 `align` 为 `l/ctr/r`。图片仅支持 PNG，额外要求 `file`、`raster_reason`、`atomic_raster_unit:true`、`contains_text:false`，并人工核对声明。

```bash
python3 scripts/prepare_powerpoint.py /absolute/scene.json --output /absolute/work/cache.pptx
python3 scripts/run-powerpoint-mac.py --cache /absolute/work/cache.pptx --job-dir /absolute/work/live --stage start
python3 scripts/run-powerpoint-mac.py --cache /absolute/work/cache.pptx --job-dir /absolute/work/live --stage step
python3 scripts/run-powerpoint-mac.py --cache /absolute/work/cache.pptx --job-dir /absolute/work/live --stage run
# 创建 job-dir/pause 文件即可在下一批之前暂停；移除该文件后再次 run。
python3 scripts/run-powerpoint-mac.py --cache /absolute/work/cache.pptx --job-dir /absolute/work/live --stage inspect
python3 scripts/run-powerpoint-mac.py --cache /absolute/work/cache.pptx --job-dir /absolute/work/live --stage finish --output /absolute/outputs/figure-live.pptx
```

`start` 复制已验证缓存为任务会话，不修改缓存。状态记录缓存哈希、目标完整路径及进度；恢复时现场读取目标形状名称与顺序，拒绝不匹配的缓存或目标。`step` 只增加一个对象；`run` 在批次之间响应暂停文件。`READY/DRAWN` 不是完成；保存后对象名称、顺序、文字内容、自由路径数及贝塞尔几何指纹回读相同才记录 `DONE`。

## 验收与能力边界

必须观察空白页、两个不同进度和最终页，测试暂停/单步/恢复。保存后核对形状、自由曲线、图片数量和全部 Unicode 文本。再用 PowerPoint 自身导出 PDF/PNG，检查标签、箭头端点、遮挡、图片边缘和参考图对应关系。脚本中的数量与文字比对只构成结构证据；不能替代外观验收。

编译器支持上述对象家族和原生路径分组；不支持表格、图表、蒙版或复杂 SVG 的通用导入。需要这些能力时用实际可用的原生接口，或报告具体限制，不把它们扁平化。所有字体和科学内容仍需现场核对。图片原子化、语义正确性和外观质量不是代码能够自动证明的。

## 复杂插画也必须逐路径绘制时

当用户要求“像 Illustrator 一样实时画小鼠/细胞，而不是贴图”时，使用 **native 模式**。本次的复杂对象通路为：

`单个复杂插画裁切 → 本机 Illustrator 高保真描摹并展开 → 导出锚点/控制点/填色/复合路径 → DrawingML 原生自由曲线 → 每批原生路径在 PowerPoint 中创建`

这里 Illustrator 仅用于准备矢量几何，实际逐批创建和最终编辑都在 PowerPoint 中。已有受支持的原生几何缓存时无需再次描摹。不要隐去该准备依赖，也不要把 SVG/EMF 图片插入当成此通路。

```bash
# Pillow 用于读取裁切并准备 TIFF；execute 在 Mac 调用已安装的 Illustrator。
python3 scripts/trace_powerpoint_assets.py /absolute/scene-hybrid-input.json --job-dir /absolute/work/vector-assets --execute
# 保留所有已核验路径；paths-per-batch 只改变传输分组，不简化曲线。
python3 scripts/import_powerpoint_vectors.py /absolute/scene-hybrid-input.json --vectors /absolute/work/vector-assets --output /absolute/work/scene-native.json --paths-per-batch 16
python3 scripts/prepare_powerpoint.py /absolute/work/scene-native.json --output /absolute/work/cache-native.pptx
# start 后先 run --until N，在复杂对象只画了一部分时检查画布；再 step / run。
```

导出器保留 Illustrator 锚点、左右控制点、闭合标记、填色和复合子路径；转换器保留曲线与顺序，复合路径作为一个原生填充对象。编译器还支持 `group`，其 `children` 使用同一画布绝对坐标。按 8–16 条路径组成一个播放组可以减少跨进程调用，内部路径仍可单独编辑。组数不能当作路径数报告。

先清理裁切中夹带的旧文字和连接器，不能先描摹再把旧字也作为路径加入最终图。原图背景透明化后用白底准备 TIFF，`ignoreWhite` 会忽略纯白区域；对象自身的重要纯白结构因此可能需要单独恢复并核对，不可无条件声称无损。可使用清单 `remove_neutral_fragments` 声明已人工确认的旧虚线碎片范围：`bounds:[left,top,right,bottom]` 和 `max_gray`；只有完整落入范围且满足中性暗色条件的路径才移除。记录移除数并视觉复查，不能为提速批量删除细节。

复杂对象导出仅接受不透明纯色填充路径；遇到裁切组、描边、透明度或未知效果会拒绝，不能静默丢失。输入图片哈希不符或缓存无来源记录时要求新任务目录，不沿用同名旧路径。现场验收必须确认小鼠/细胞出现过 **部分路径完成** 的中间态，并在保存文件内检查 `a:custGeom`、贝塞尔节点、组内路径和零 `p:pic`。SVG 图片、预置动画、隐藏后揭示都不能满足这个测试。

绘制方式的源码依据、复合路径与可见过程的区别见 [cell-lct / cell_su7 对照](drawing-methods.md)。Mac 创建路线默认不增加延时；教学演示时可显式设置 `--delay`。
