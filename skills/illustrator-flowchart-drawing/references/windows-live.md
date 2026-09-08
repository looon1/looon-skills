# Windows 入口与实时绘制

## Windows

需要已安装的桌面 Illustrator、Python 3、Pillow，以及交互式 Windows 桌面会话。建议从 Windows PowerShell 5.1 启动；提供的 COM 入口尚未在 Windows 实机验证。不能把 Linux SSH 会话或无桌面服务器说成可以展示 Illustrator 绘制过程。

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\scripts\prepare_job.py C:\Figures\reference.png `
  --job-dir C:\Figures\work\job1 --output-dir C:\Figures\output\figure1

.\scripts\run-illustrator.ps1 -JobDir C:\Figures\work\job1 -Stage inspect
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\work\job1 -Stage trace

# 核对描摹预览并编写 labels.json 后，再准备重建脚本。
.\.venv\Scripts\python.exe .\scripts\prepare_job.py C:\Figures\reference.png `
  --job-dir C:\Figures\work\job1 --output-dir C:\Figures\output\figure1 `
  --manifest C:\Figures\work\labels.json
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\work\job1 -Stage rebuild
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\work\job1 -Stage verify
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\work\job1 -Stage live
```

启动器通过 `Illustrator.Application` COM 对象执行生成的 JSX，并检查当次日志。它不会调用 `Quit()`，也不会更改系统或用户的脚本执行策略。若本机阻止 PS1，直接在 Illustrator 的“文件 → 脚本 → 其它脚本”中执行同一个 JSX；不要为了运行本 Skill 全局关闭执行策略。

英文和中文高保真照片预设会自动匹配。其他语言使用 `inspect.jsx` 输出的真实预设名，在 JSON 清单顶层设置 `preset`。若字体不同，按真实 PostScript 字体名调整各 label。

## Illustrator 画布中的实时绘制

`live.jsx` 先读取一次源稿的贝塞尔锚点、控制柄和文字属性，在独立 Illustrator 文档中逐批创建原生路径与活文字；每 8 个叶对象调用 `app.redraw()`，短暂停顿 40 ms，每层结束再刷新。用户可以看到底板、插画细节、文字逐步出现；这不是录制视频，也不是完整位图逐帧叠放。该实现避开了实测出现 `MRAP` 错误的跨文档 `duplicate()`。

这是一种经整理的矢量结果的逐步创建过程，不是逐笔还原人类画图动作，也不是实时生成新的语义内容。描摹计算本身仍可能有等待时间；先完成重建与验收再播放，可以避免把字体修复和错误重试展示在绘制过程中。

- 将 Illustrator 窗口放到用户希望观看的显示器，调整到适合画板大小的视图。
- 运行前保留源 AI；`figure-live.ai` 和 `preview-live.png` 另存。已有同名实时稿时使用新的输出目录或经用户授权处理旧文件。
- 播放脚本面向本 Skill 生成的 RGB 填充路径与单一格式点文字。复合路径、裁切组、渐变、实时效果、特殊混合或插件对象不在此入口的验证范围内；遇到不支持的对象应另写适配器，不能静默丢弃。
- 验证实时稿与源 AI 的文字、路径数量一致，并比较两张导出 PNG。数量相同并不能排除堆叠或色彩错误，视觉检查仍必需。
