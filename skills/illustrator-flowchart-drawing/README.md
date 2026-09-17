# Illustrator / PowerPoint 参考图重建与实时绘制

普通文字、框线、箭头、虚线和基础几何一次创建为原生可编辑对象，只有复杂插画在 Illustrator 画布中分批出现。控制面板支持开始、暂停、单步与继续；等待发生在应用外，画布有时间刷新。

本地 Illustrator 负责复杂插画描摹，无需上传到第三方识别服务、部署服务器或下载模型权重。参考图转录、插画区域和保真判断仍需要 Agent 看图核对，不是无人审核的自动复刻器。

## 安装

将本目录放入 `~/.codex/skills/illustrator-flowchart-drawing/`；Windows 对应 `%USERPROFILE%\.codex\skills\illustrator-flowchart-drawing\`。在本目录运行：

```bash
python3 setup.py --formulas
.venv/bin/python scripts/doctor.py --formulas
```

Windows PowerShell：

```powershell
py setup.py --formulas
.\.venv\Scripts\python.exe scripts\doctor.py --formulas
```

需要 Python 3.10–3.14 和桌面 Illustrator。`setup.py` 仅安装锁定版本的 Python 依赖到 `.venv`。公式另需已安装的 TeX Live：`xelatex`、`dvisvgm`、`kpsewhich`、`unicode-math`、`standalone`、XITS 字体；无公式可省略 `--formulas`。不自动安装应用或修改系统设置。

## 使用提示词

> 使用 $illustrator-flowchart-drawing 将参考图高保真复刻为可编辑的 Adobe Illustrator 矢量图。严格保持原图的画布比例、布局、尺寸、位置、连线、箭头、线宽、颜色和层级，不擅自增删或改动。框体、节点、线条、符号和图标均重建为独立矢量对象；文本、框线、箭头、虚线等基础元素原生生成并一次出现，仅复杂插画逐步绘制。
>
> 逐字核对全部数学公式，使用正规数学排版生成真正的上下标、分式、希腊字母、求和上下限、帽符号和运算符，禁止 Unicode 近似上下标或普通文本拼凑。变量使用数学斜体，准确控制上下标字号、基线和间距。公式、正负号及普通文字统一使用真实粗体，变量为真实数学粗斜体，不得重复叠加或用描边模拟加粗。统一粗体是明确的样式调整，其余属性仍按原图。
>
> 普通文字保留可编辑文本框；公式无法稳定编辑时，将正规排版结果转为清晰矢量轮廓，并保留可重新生成的公式源码。完成后放大核查错字、乱码、缺笔画、公式错位、重复对象和线条遮挡，导出同画板比例的 PNG 复核，交付 AI、PNG、Master SVG、公式清单与源码。

入口见 [SKILL.md](SKILL.md)，字段见 [清单格式](references/manifest.md)，平台命令见 [实时启动器](references/windows-live.md)。含公式时内置 XeLaTeX → XDV → dvisvgm 排版与复合矢量导入，不描摹公式截图。普通文字按真实字号/基线定位，多行与旋转保持可编辑；缺字、字体不是真粗体时明确失败。

## 工作流与输出

- 参考图：`inspect → trace → 编写并核对 manifest → rebuild → verify → live → verify`。
- 已有完整原生对象清单：`compose → verify → live → verify`。
- 本 Skill 旧版未整理结构的 AI：复制为任务输入后 `structure`，迁移旧文字度量并原生重建结构。
- `figure.ai` / `figure-live.ai`：最终可编辑 AI；普通文字是 TextFrame，公式是带源码的矢量轮廓。
- `preview.png`、`master.svg`：同一最终已保存并重新打开的 AI 导出，保持画板比例；SVG 普通文字保留 text 元素。
- `formulas.json`、`formulas/<ID>/source.tex`、`outline.svg`：公式完整源码、位置、字体文件指纹、引擎、编辑方式和核验状态；无公式为 `[]`。
- `fonts.json`、`native-audit.json`、`verification.json`：字体证据、原生对象回读、导出文件与差异检查。

可恢复的批次保存稳定对象 ID、输入指纹和磁盘检查点。重新运行相同任务可跳过已创建对象；更换清单或脚本时使用新任务目录。首批始终是静态对象；后续默认每批 8 项、应用外间隔 500 ms。复合字形和剪切组保持完整，不拆散孔洞。

## 测试和限制

```bash
.venv/bin/python scripts/self_test.py
.venv/bin/python scripts/test_regressions.py
.venv/bin/python scripts/test_powerpoint.py
# 需要真实桌面 Illustrator；创建独立测试文件，输出目录必须尚不存在：
.venv/bin/python scripts/test_desktop.py --output-dir /absolute/new-desktop-test
```

CI 执行 Python 检查，不宣称托管环境运行了 Illustrator。详细实测证据见 [验证记录](references/validation.md)。Mac Illustrator 29.5.1 已执行本次原生公式、文字、复合孔洞、剪切、播放与恢复验收；Windows 实机验收待可连接环境。

自动检查结构与文件一致性，不能判定公式科学含义或与参考图完全一致。局部字体渲染可能产生少量边缘像素差异；原图保真、源稿到实时稿、AI 保存回读、SVG 回读分别记录。支持的对象与输入边界见 SKILL，不静默栅格化不支持内容。

## PowerPoint 分支

用户指定 PowerPoint 时在 PowerPoint 展示与编辑。简单几何无需 Illustrator；复杂插画逐路径模式使用本机 Illustrator 描摹准备矢量。macOS 提供 DrawingML 几何缓存编译器与 AppleScript 逐对象实时播放，支持原生文字、自由贝塞尔曲线、箭头、渐变及明确声明的原子图片。完整命令、暂停恢复和验收边界见 [PowerPoint 实时绘制](references/powerpoint-live.md)。Windows 使用可用的 PowerPoint COM/MCP 接口；本次新增 Mac 脚本不宣称验证了 Windows。

`native` 模式拒绝图片；`hybrid` 模式必须披露图片数量。逐对象播放会创建一个独立任务演示文稿，保存后比对原生对象顺序及全部文本。模板仅是空白 PowerPoint 文件，最终几何通过缓存导入到空白目标页；不以整页截图或动画揭示冒充实时绘制。

复杂插画支持先展开真实锚点、贝塞尔控制点及填色，再分批创建 PowerPoint 原生自由曲线。小鼠与细胞不必作为图片插入；`paths-per-batch` 只控制每次传输的组大小，不减少细节。详见 PowerPoint 分支的复杂插画章节。
