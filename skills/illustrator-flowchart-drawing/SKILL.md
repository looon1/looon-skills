---
name: illustrator-flowchart-drawing
description: 将参考图片中的流程图、信息图和插画重建为 Adobe Illustrator 可编辑文件，支持 macOS 原生脚本、Windows 启动入口与画布实时绘制。适用于还原原图、恢复可编辑文字并交付经 Illustrator 验证的 AI、SVG 和 PNG 的任务。
---

# Illustrator 参考图重建

以参考图为视觉依据，保留文字内容、相对位置、配色和插画轮廓。默认目标是外观接近且便于编辑；若用户要求像素级一致，说明描摹与字体重建会产生细微差异。不要把一张嵌入位图称为可编辑矢量重建，也不要补写图片没有提供的科学内容。

## 先确认可执行环境

- 检查实际可用的 Illustrator 会话、版本、脚本执行入口与字体。一个已连接的 Linux 服务器并不等于可运行 Illustrator；本机 Illustrator 可用时可直接完成任务。
- 有可用文档连接器时先检查会话及支持的命令。否则通过当前环境允许的电脑控制工具执行 Illustrator 的“文件 → 脚本 → 其它脚本”。不要因为连接器没有会话就判断 Illustrator 不可操作。
- 按原图真实像素尺寸建画板。截图在聊天中可能被缩放，标注坐标必须换算到原始尺寸。
- 脚本与任务输入放在本次任务的工作目录。不要写死上一次任务的文件路径、窗口编号、文档名、预设语言或服务器地址。

本流程最初在 macOS、Illustrator 2025 29.5.1 中验证。其他版本须现场检查，不要求安装 Cell-lct，也不宣称已验证其 Windows 工作流。

## 执行顺序

1. **准备与描摹**：检查原图，运行下方准备命令。在 Illustrator 执行生成的 `inspect.jsx`，查看 `environment.txt` 中的预设和字体，再执行 `trace.jsx`。检查 `trace.log` 和 `trace-preview.png`。脚本使用原图像素值生成独立 TIFF，再用 `app.open()` 获得 RasterItem；这条路径曾成功解决 PNG 置入失败，但失败根因未被证实。
2. **文字与分组**：根据实际原图创建文字和插画区域清单。读 [清单格式](references/manifest.md)，不要复制示例坐标。再次准备任务并传入 `--manifest`，执行 `rebuild.jsx`。所有可辨认文字均恢复为原生 `TextFrame`，包括插画内缩写、结构式字母、上下标和符号。单行标签使用点文字文本对象，可以直接编辑内容与字体；不要将最终文字转曲。
3. **验收**：执行 `verify.jsx`，重新打开保存的 AI，检查文本内容、符号、画板、路径数及位图数。读取 `verify.log`，并在 Illustrator 中观察成品、查看导出的 PNG；仅有“保存成功”不算通过。人工对照原图确认清单没有漏字；仅统计清单内文字不能证明覆盖了全部文字。最终选择一处标题和一处插画小字，确认 Illustrator 显示字符、字体与段落属性。
4. **实时绘制（用户要求时）**：在验收后的成品基础上执行 `live.jsx`，在一个新画板里按底板、插画、文字的顺序分批创建对象。原稿保留，实时稿另存为 `figure-live.ai`。读 [Windows 与实时绘制](references/windows-live.md)，尤其注意版本验证与可视桌面要求。

准备命令（Python 需要 Pillow）：

```bash
python /path/to/skill/scripts/prepare_job.py /absolute/reference.png \
  --job-dir /absolute/work/figure-job \
  --output-dir /absolute/outputs/figure

# 原生描摹完成、确认文字和分组坐标后，再生成重建脚本。
python /path/to/skill/scripts/prepare_job.py /absolute/reference.png \
  --job-dir /absolute/work/figure-job \
  --output-dir /absolute/outputs/figure \
  --manifest /absolute/work/labels.json
```

`trace.ai` 是文字仍为轮廓的内部中间稿，绝不能当作成品展示。描摹检查后继续完成文字恢复；结束时将最终 `figure.ai` 或 `figure-live.ai` 留在 Illustrator 前台。

这些命令只准备文件，不会自己启动或遥控 Illustrator。通过已获授权的应用接口或 UI 执行 JSX。生成的脚本使用 ASCII 转义保存 Unicode，输出日志使用 UTF-8。

## 重建与验收要点

- 高保真照片预设配合 `pathFidelity=90`、`cornerFidelity=80`、`noiseFidelity=1` 是这类平面插画的已验证起点，不能保证适合每张图。先看描摹结果，再决定是否调整。
- 保留平面底板与连接箭头，将完整落入区域的插画路径按原堆叠顺序移入独立组。跨出区域的路径不会被自动裁切；检查是否遗漏轮廓或遮挡。
- 用文字轮廓副本测量实际墨迹边界，再定位活文字。自动贴合边框只能匹配范围，不能证明字体相同；过度压缩的字形需要重新选字体或修正边框。
- 仅在纯色背景上使用文字背景补片。渐变、纹理、透明区域与重叠文字需要单独处理，不能用大矩形粗暴覆盖。检查文字删除范围及背景补片边缘。
- 单独检查 `≥`、`≤`、希腊字母、上下标和单位。控制台乱码不等于文件乱码；以重新打开的 AI、导出 PNG 及文本的 Unicode 为准。
- 主文件保存为 PDF-compatible AI。SVG 使用 `SVGFontSubsetting.GLYPHSUSED`，避免嵌入整套字体造成文件异常膨胀。导出后不要依赖活动文档名称或 `fullName` 判断已保存的 AI；重新打开明确的 AI 路径。
- 仅处理本次任务创建的文档。不要按“未标题-2”之类的名字猜测可丢弃文件，也不要无条件关闭活动文档。

如遇 PNG 置入、中文文件选择器、预设或脚本错误，按 [运行与排错](references/runtime.md) 处理。相同失败重复出现时先读日志并换有依据的路径，不要盲目重放 UI 操作。

交付 AI、PNG，按需要附 SVG；报告实际活文字数量、插画分组数量及保真限制。若原生 Illustrator 验证未完成，明确标记未验证，不能把生成了 SVG 或安装了 Skill 当作任务完成。
