# Mac / Windows 启动器与实时绘制

两个平台使用相同 JSX 和对象格式：Mac 通过 Illustrator 原生 AppleScript，Windows 通过 `Illustrator.Application` COM。需要已安装 Illustrator 的交互式桌面。Linux SSH、COM 注册成功、Python 单元测试均不等于实际可见绘制。

## Windows

建议 Windows PowerShell 5.1，Python 3.10–3.14。首次在 Skill 目录运行 `py setup.py --formulas`；无公式可省略开关。公式依赖见 [公式参考](formulas-fidelity.md)。

```powershell
.\.venv\Scripts\python.exe scripts\prepare_job.py C:\Figures\reference.png `
  --job-dir C:\Figures\job1 --output-dir C:\Figures\output1
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\job1 -Stage inspect
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\job1 -Stage trace
# 核对描摹预览并完成清单后：
.\.venv\Scripts\python.exe scripts\prepare_job.py C:\Figures\reference.png `
  --job-dir C:\Figures\job1 --output-dir C:\Figures\output1 --manifest C:\Figures\manifest.json
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\job1 -Stage rebuild
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\job1 -Stage verify
.\scripts\run-illustrator.ps1 -JobDir C:\Figures\job1 -Stage live
# 如需启动即播放，加 -Start；-MaxBatches 1 可在首批后暂停。
```

启动器检查当次阶段日志和互斥锁，释放自己持有的 COM 句柄，不调用 Quit、不关闭用户文档、不修改系统执行策略。PS1 被策略阻止时按该机器的既有管理规则处理；非实时阶段可从 Illustrator“文件 → 脚本 → 其它脚本”执行生成的 JSX，实时阶段仍需要能运行的外部启动器。

本地验收入口：

```powershell
.\.venv\Scripts\python.exe scripts\test_desktop.py --output-dir C:\Figures\new-desktop-test
```

输出目录必须尚不存在；验收只创建、保存及关闭自身测试文件。Windows **实机验收尚待完成**，收到可连接的桌面环境后执行该入口并核对实际画布。不能使用 Mac 结果替代。

## macOS

```bash
.venv/bin/python scripts/run-illustrator-mac.py --job-dir /absolute/job --stage live
# 自动开始并在一批后暂停：
.venv/bin/python scripts/run-illustrator-mac.py --job-dir /absolute/job --stage live --start --max-batches 1
.venv/bin/python scripts/test_desktop.py --output-dir /absolute/new-desktop-test
```

若环境要求 AppleScript 授权，遵循当前工具规则；用户已授权的同一用途不重复询问。原生调用有超时，遇到超时先看日志与画布，不立即排队重复调用。

## 画布与控制

`live` 先捕获已核验 `figure.ai` 的对象几何、复合轮廓、剪切和活文字属性，创建独立空白画板和控制面板。系统启动器逐批调用 Illustrator，**每次调用返回后**才等待，保证应用有机会刷新画布。单次长脚本内 `app.redraw()`/`$.sleep()` 不能替代外部让出执行。

首批完整创建背景、框线、箭头、虚线、普通文字和全部排版公式。后续仅创建名称以 `02 Illustrations` 开头的图层中复杂插画；默认每批 8 项、间隔 500 ms，可在清单 `playback` 中调整。普通分组可递归分批；复合路径和剪切组作为完整原子，复杂度很高时单批仍可能较慢，不能拆掉孔洞来提速。

- `Start / Resume`：播放/继续。
- `Pause`：当前批次完成后停止提交下一批。
- `Step`：只推进一批，再保持暂停。
- 关闭面板或 Ctrl+C：保留部分文档；重新运行同一 `live` 入口可继续。

`READY` 只代表面板就绪；`DONE` 表示最后一批通过检查并完成 AI/PNG/SVG 导出。只运行 JSX 不会自动持续播放，需要外部启动器。播放是预先核验的复杂几何逐步创建，不声称实时生成新语义或模拟人类每一笔。

## 恢复与一致性

- `live-session.json` 记录输入指纹、会话标识、对象统计与完成状态；`live-batches/*.json` 是不可变批次几何；同名 JSX 调用完整编译运行时，不序列化函数源码。
- 稳定对象 ID 保存在对象 note。批次游标只有整批完成才递增；重试跳过已存在的完整对象，未成功创建的原子回滚后补建。
- 首批和之后约每 60 秒保存任务自有 `live-checkpoint.ai`。文档关闭后重开检查点、重新核对各对象，再补齐未持久化部分；已经完成的任务重新打开最终 `figure-live.ai`。
- 当前恢复验收覆盖：对象完成后、游标提交前打断；部分画板关闭后从磁盘恢复；完成后重新打开。同样不能宣称能恢复任意磁盘损坏或所有进程崩溃时刻。
- 使用任务锁避免两个启动器同时写一个 job。清单、图像或运行时代码改变时拒绝续用原 live job，使用新的 job/output。
- 人工更改部分绘图不是自动合并功能；若修改过对象，先另存备份并重新核对，不能假定 ID 相同就等于几何未改。

首批与至少两个中间画布都需现场观察；暂停与单步需检查进度和实际对象数。最终运行 `verify`，比较源稿→实时稿、保存回读以及 SVG 回读的 PNG，分别记录差异。对象数相等不能替代外观核验。完成后将最终 AI 留在前台。
