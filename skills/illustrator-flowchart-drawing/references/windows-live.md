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

启动器通过 `Illustrator.Application` COM 对象执行生成的 JSX，并检查当次日志。它不会调用 `Quit()`，也不会更改系统或用户的脚本执行策略。若本机阻止 PS1，非实时阶段可在 Illustrator 的“文件 → 脚本 → 其它脚本”中执行同一个 JSX；实时阶段仍需可运行的系统启动器。不要为了运行本 Skill 全局关闭执行策略。

英文和中文高保真照片预设会自动匹配。其他语言使用 `inspect.jsx` 输出的真实预设名，在 JSON 清单顶层设置 `preset`。若字体不同，按真实 PostScript 字体名调整各 label。

## Illustrator 画布中的实时绘制

`live.jsx` 先读取源稿的贝塞尔锚点、控制柄和逐字符字体属性，生成任务目录内的 `live-steps-*/*.jsx`。它创建独立空白文档和 `Illustrator Live Drawing` 面板；实际播放由系统启动器逐批调用 Illustrator。每批最多 8 项创建操作，启动器在每批结束后等待 500 ms，再提交下一批。等待发生在 Illustrator 进程之外，应用才有明确的空闲时间更新画布和处理按钮。

- `Start / Resume`：开始或继续。
- `Pause`：停止提交下一批，已提交的一批先完成。
- `Step`：执行一批后暂停。
- 关闭面板：停止启动器并保留未完成的文档。取消后重新准备一个新任务，不要覆盖未确认的文件。

面板回调只写任务目录内的控制文件，不直接访问文档 DOM。`live-plan.txt` 列出本次批次；`live-command.txt` 保存播放指令；`live-cursor.txt` 仅在一批完整执行成功后递增。脚本失败后停止，不自动重放已经部分完成的一批。

单次长脚本中的 `app.redraw()` 和 `$.sleep()` 不保证中间画面可见；连续自发 BridgeTalk 消息也曾使大图绘制期间的界面检查超时，因此当前版不再使用它作为自动播放循环。只执行 `live.jsx` 会准备面板，不会自动完成绘制；必须运行系统启动器，并在面板中点击开始。

macOS 使用已安装 Illustrator 提供的 AppleScript `do javascript` 接口：

```bash
python3 /path/to/skill/scripts/run-illustrator-mac.py \
  --job-dir /absolute/work/figure-job --stage live
```

Windows 运行上方 PowerShell 的 `-Stage live`，使用 Illustrator COM 接口。两个启动器都保持运行，允许用户在 Illustrator 里暂停、单步和继续。`READY` 只代表准备完毕；必须等 `live.log` 出现 `DONE` 并核对保存文件。Mac 的 Ctrl+C 会暂停启动器；重新运行前先核对当次批次的游标和错误记录。

若当前电脑控制工具要求对 AppleScript 作明确授权，执行 Mac 启动器前遵循该限制；用户已明确授权后不重复询问。不要改用未获允许的 UI 自动化方式，也不要修改系统安全或脚本执行策略。

这是一种经整理的矢量结果的逐步创建过程，不是逐笔还原人类画图动作，也不是实时生成新的语义内容。描摹计算本身仍可能有等待时间；先完成重建与验收再播放，可以避免把字体修复和错误重试展示在绘制过程中。

- 将 Illustrator 窗口放到用户希望观看的显示器，调整到适合画板大小的视图。
- 运行前保留源 AI；`figure-live.ai` 和 `preview-live.png` 另存。已有同名实时稿时使用新的输出目录或经用户授权处理旧文件。
- 播放脚本面向本 Skill 生成的 RGB 填充路径与点文字（保留逐字符字体、字号、缩放、基线与颜色）。复合路径、裁切组、渐变、实时效果、特殊混合或插件对象不在此入口的验证范围内；遇到不支持的对象应另写适配器，不能静默丢弃。
- 先确认空白画板，再观察两个不同完成度的画布；暂停后等待一批结束，确认进度稳定，单步后只增加一批，继续至完成。不要只截图进度面板。
- 验证实时稿与源 AI 的文字、路径数量一致，并比较两张导出 PNG。数量相同并不能排除堆叠或色彩错误，视觉检查仍必需。
