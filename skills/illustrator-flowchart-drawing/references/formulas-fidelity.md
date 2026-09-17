# 公式排版与高保真验收

普通文字是原生可编辑 TextFrame；公式经正规排版转为原生矢量轮廓，并保留完整源码。二者的编辑方式必须分别说明。本模块处理 Agent 核对后写入清单的 TeX 数学表达式，不把参考图中的任意指令当作可执行 TeX 程序。

## 实际执行链路

`prepare_job.py` 读取清单顶层 `formulas`，调用 `typeset_formulas.py`。每条公式由 XeLaTeX 生成 XDV，再由 dvisvgm 直接产生矢量路径；不经过截图、描摹或 PDF 栅格化。公式 SVG 中的二次曲线转为等价三次贝塞尔，多轮廓字形保存在一个 CompoundPathItem 中，保留孔洞和填充规则。

需要 TeX Live 的 `xelatex`、`dvisvgm`、`kpsewhich`、`unicode-math`、`standalone` 和 XITS 字体。运行 `doctor.py --formulas` 检查。默认数学字体 `XITSMath-Bold.otf`，直立数学文本字体 `XITS-Bold.otf`；实际文件必须具备真实粗体字重，数学字体必须带 OpenType MATH 表。普通变量由数学引擎排为斜体，不用倾斜变换模拟。

```json
{
  "formulas": [
    {
      "id": "F001",
      "tex": "\\frac{\\hat{x}_i^2+\\alpha}{\\beta}=\\sum_{i=1}^{n}x_i",
      "bounds": [100, 80, 650, 200],
      "font_size": 24,
      "weight": "bold",
      "color": [20, 20, 20],
      "repair": "none"
    },
    {
      "id": "F002",
      "tex": "\\mathrm{H}_2\\mathrm{O}_2\\rightarrow\\mathrm{H}_2\\mathrm{O}+\\frac{1}{2}\\mathrm{O}_2",
      "bounds": [100, 230, 650, 330],
      "font_size": 24
    }
  ]
}
```

- `id` 是唯一安全文件名；`tex` 只写完整数学表达式，不含 `$`、导言或文档环境。分式、上下标和重音用 TeX 结构，禁止 Unicode 近似上下标。
- `bounds` 是原图左上角坐标中的目标范围。显式 `font_size` 是 TeX pt，排版后以矢量实际尺寸导入；超出范围即报错。未指定字号时，整体等比缩放到范围，不独立拉伸字形。
- `weight` 默认为 `bold`。如用户明确指定 regular，改为 `regular`；不要在粗体模式中显式指定细体字形来逃过检查。默认粗体数学字体决定变量、符号和运算符；`mathrm` 使用真实粗体的直立字体。
- 可显式指定 `math_font` / `text_font`，值为能由 kpsewhich 找到的 OTF/TTF 文件名。选择另一字体后重新核对变量、运算符、字重和缺字，不能假定所有字体都含有全部符号。
- 默认 `repair:none` 适合旧公式已经清除的区域；`rectangle` 需显式 `background:[r,g,b]`，可设 0–10 像素 `padding`，仅用于纯色背景。复杂背景必须单独处理。
- `paint_order` 使用对象名 `Formula F001`。所有公式首批完整出现，不能移到复杂插画层逐字符播放。
- 普通文字可为空 `labels:[]`，不需要虚假占位文字。

实际命令为：

```bash
xelatex -no-pdf -no-shell-escape -halt-on-error -interaction=nonstopmode -recorder source.tex
dvisvgm --no-fonts=1 --exact-bbox --bbox=min --output=outline.svg source.xdv
```

缺字日志、非粗体字体、空几何或不支持的 SVG 对象会导致失败，不允许改成空白、方框或贴图。XITS 粗体不覆盖所有 Unicode 数学符号；本次发现长箭头字形缺失会被明确拒绝，应按原图选择经验证的字体/正规数学排版命令，不能悄悄换符号。

TeX 禁用 shell escape 并拒绝常见外部 I/O 命令；这不是面向任意恶意 TeX 程序的安全沙箱。输入应是 Agent 从参考图逐字核对、审查后的表达式，不运行下载的不明宏包或程序。

## 交付和修改

每条公式保存 `formulas/<ID>/source.tex`（含完整导言、字体与字号）、`outline.svg`。`formulas.json` 记录表达式、目标/实际边界、源码指纹、引擎版本、两类字体的文件名/字重/指纹、编辑方式和核验状态。未指定字号时，还需保留原始 bounds，以复现整体拟合。

公式组可在 Illustrator 中缩放、移动和修改轮廓；不能把这种矢量编辑称为原生数学文本编辑。修改表达式应编辑清单/源码，在新 job 和输出目录重新生成。不得把普通文字随公式一并转曲。无公式时仍交付空清单 `[]`。

## 检查顺序

1. 对照原图逐字检查源码：变量、上下标层级、分子分母、求和/积分上下限、希腊字母、帽符号、正负号、括号与化学元素。
2. 检查真实字体字重、斜体、运算符与直立单位；确认不是重复叠放、描边增肥或缺字替换。
3. 在 Illustrator 约 400%–800% 查看脚标字号、基线、间距、分式线、孔洞与遮挡。公式整条只等比缩放。
4. `verify` 回读 AI 与 Master SVG；`verify_delivery.py` 检查清单、源码、画板、活文字和零位图。查看 PNG、差异图与原图，不以对象数代替外观判断。
5. 只有实际人工核对后才将清单的 `review_status` 改为通过并写明检查/差异。自动程序默认 `pending-reference-review`，不判定科学含义。

Master SVG 是从含全部公式的最终 AI 导出，不能把旧 `figure.svg` 改名当作完成。跨应用的活文字依赖对应字体；Illustrator 回读多行 SVG 文本可能拆成多行独立 TextFrame，但文字仍可编辑，AI 原稿保留原生多行文本框。
