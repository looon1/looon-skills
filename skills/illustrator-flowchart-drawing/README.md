# Illustrator / PowerPoint 参考图重建与实时绘制

Illustrator 分支把参考图重建为可编辑 AI：复杂插画为矢量路径，文字、框线、箭头、虚线及简单背景使用原生对象。运行系统启动器的 `live` 阶段后先显示空白画板和控制面板，点击 `Start / Resume` 开始；支持暂停与单步绘制。系统启动器逐批调用 Illustrator，并在应用外等待半秒，让画布和控件在批次之间响应。

本版本直接替换旧 SuperSVG 工作流，使用本机 Illustrator 描摹和 JSX；不需要服务器部署或模型权重。保留原 Skill 名称 `illustrator-flowchart-drawing`。

## 安装与使用

将本目录复制到 Codex 的 `~/.codex/skills/illustrator-flowchart-drawing/`。Windows 的对应位置为 `%USERPROFILE%\.codex\skills\illustrator-flowchart-drawing\`。随后用自然语言指定参考图和输出目录，例如：

> 使用 $illustrator-flowchart-drawing 重建这张图。所有文字必须能直接编辑，并在 Illustrator 中展示逐步绘制过程。

Python 依赖建议放在隔离环境内：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/self_test.py
```

Windows PowerShell：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\self_test.py
```

执行顺序为 `inspect → trace → 编写文字与 nativeLayout 清单 → rebuild → verify → live`。已有可编辑 AI 时可通过 `--editable-source` 和 `structure` 阶段重组。实时阶段必须运行系统启动器：Mac 用 `scripts/run-illustrator-mac.py --job-dir /absolute/job --stage live`，Windows 用 `scripts/run-illustrator.ps1 -JobDir C:\Figures\job -Stage live`；单独运行 `live.jsx` 只准备空白画板和控制面板。完整入口见 [SKILL.md](SKILL.md)，Windows 命令见 [Windows 与实时绘制](references/windows-live.md)。`trace.ai` 的文字仍是描摹路径，只用于内部检查，不能交付为成品。

## 输出与验证

- `figure.ai`：主 AI，文字保留为原生 `TextFrame`。
- `figure.svg`、`preview.png`：矢量交换文件及预览。
- `figure-live.ai`、`preview-live.png`：逐步创建得到的独立成品。
- 任务目录中的各阶段日志：核对文本内容、路径、分组与零位图。

2026-09-10 在 macOS Illustrator 29.5.1 中以复杂机制图验证：首批完整创建 45 个原生文本框及框线、箭头、虚线和背景，复杂插画为零；矩形框有 4 个锚点，虚线保留原生描边属性。后续只逐步创建复杂插画，并通过暂停、单步与继续检查。最终成品包含 2,290 条路径、45 个文本框和 20 个插画组，位图及置入对象为零；保存回读后的 PNG 与完成稿逐像素一致。13 项准备脚本测试通过。每个新任务仍须按 SKILL.md 验收。Windows 提供同一 JSX 配合 PowerShell/COM 启动器，尚未在 Windows 实机运行。逐步绘制使用预先核验的矢量几何，不代表模拟人类每一笔动作。

文字内容与几何关系需要逐项对照原图；字体与阴影可能有细微差异。文件可编辑不等于原图像素级一致。适用输入为单页不透明 RGB 图像；透明、CMYK、特殊效果与复杂剪切需要单独处理。

## PowerPoint 分支

用户指定 PowerPoint 时在 PowerPoint 展示与编辑。简单几何无需 Illustrator；复杂插画逐路径模式使用本机 Illustrator 描摹准备矢量。macOS 提供 DrawingML 几何缓存编译器与 AppleScript 逐对象实时播放，支持原生文字、自由贝塞尔曲线、箭头、渐变及明确声明的原子图片。完整命令、暂停恢复和验收边界见 [PowerPoint 实时绘制](references/powerpoint-live.md)。Windows 使用可用的 PowerPoint COM/MCP 接口；本次新增 Mac 脚本不宣称验证了 Windows。

`native` 模式拒绝图片；`hybrid` 模式必须披露图片数量。逐对象播放会创建一个独立任务演示文稿，保存后比对原生对象顺序及全部文本。模板仅是空白 PowerPoint 文件，最终几何通过缓存导入到空白目标页；不以整页截图或动画揭示冒充实时绘制。

复杂插画支持先展开真实锚点、贝塞尔控制点及填色，再分批创建 PowerPoint 原生自由曲线。小鼠与细胞不必作为图片插入；`paths-per-batch` 只控制每次传输的组大小，不减少细节。详见 PowerPoint 分支的复杂插画章节。
