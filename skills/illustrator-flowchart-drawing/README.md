# Illustrator 参考图重建与实时绘制

把参考图重建为可编辑 AI：插画为矢量路径，所有可辨认文字恢复为 Illustrator 原生文本对象。可在 Illustrator 画布中逐批创建路径和文字，观看成品形成过程。

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

执行顺序为 `inspect → trace → 编写文字清单 → rebuild → verify → live`。完整入口见 [SKILL.md](SKILL.md)，Windows 命令见 [Windows 与实时绘制](references/windows-live.md)。`trace.ai` 的文字仍是描摹路径，只用于内部检查，不能交付为成品。

## 输出与验证

- `figure.ai`：主 AI，文字保留为原生 `TextFrame`。
- `figure.svg`、`preview.png`：矢量交换文件及预览。
- `figure-live.ai`、`preview-live.png`：逐步创建得到的独立成品。
- 任务目录中的各阶段日志：核对文本内容、路径、分组与零位图。

macOS Illustrator 2025 29.5.1 已完成实际重建、回读和实时绘制验证。Windows 提供同一 JSX 配合 PowerShell/COM 启动器，尚未在 Windows 实机运行。逐步绘制使用预先核验的矢量几何，不代表模拟人类每一笔动作。

文字内容与几何关系需要逐项对照原图；字体与阴影可能有细微差异。文件可编辑不等于原图像素级一致。适用输入为单页不透明 RGB 图像；透明、CMYK、特殊效果与复杂剪切需要单独处理。
