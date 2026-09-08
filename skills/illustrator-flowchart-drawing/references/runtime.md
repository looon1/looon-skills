# 运行与排错

## JSX 的执行入口

macOS Illustrator 可通过“文件 → 脚本 → 其它脚本”选择 JSX；本次验证的快捷键为 Command+F12。使用当前可用的应用自动化接口，不绕过工具的 UI 控制限制。

使用 CUA 时：

1. 选择实际 Illustrator App，读当前状态后打开脚本文件选择器。
2. 从最新可访问性树定位目标 JSX。在本次中文 macOS 文件选择器中，文件文本控件暴露的 `打开“访达”项目` 次级操作可直接执行选择；单击文件文字和连续快捷键曾无效。
3. 次级操作仅在当次状态明确暴露时使用。另一种方式是 Command+Shift+G，等前往路径表单出现后设置 `PathTextField`，确认选中文件，再点击“打开”。粘贴路径超时时可以对已观察到的文本控件使用 `setValue`。
4. 操作后读取新状态；不要跨窗口复用编号，不要把工具调用返回误认为脚本已经完成。通过任务日志确认 `DONE` 或 `ERROR`。

如果 JSX 日志长期没有进度，且应用没有错误日志，先检查真实前台与可见提示。不要反复排队提交脚本、强退 Illustrator 或丢弃未保存文档。每个标签完成后记录进度，便于定位具体文字。

## 已观察到的问题

| 症状 | 已验证处理 | 不应推出的结论 |
| --- | --- | --- |
| `Unable to set placed item's file`、`[UNKN]` | 使用独立 TIFF，通过 `app.open()` 取得 `RasterItem` 再调用 `trace()` | 没有证据证明所有 PNG 都不支持，也没有证据认定 ICC 就是根因 |
| 文档连接器返回无会话 | 检查本机 Illustrator；本次仍可通过原生脚本操作 | 不等于 Illustrator 不可用 |
| `≥` 变成方框或乱码 | 用 ASCII JSX 中的 `\u2265`，重新导出并重新打开 AI 核查 | 不要只看日志编码，也不要把符号改成不等价文字 |
| SVG 大到数十 MB | `fontSubsetting = SVGFontSubsetting.GLYPHSUSED` | 不需要为了缩小体积把主 AI 的文字全部转曲 |
| 导出后 `fullName` 指向 SVG | 保持明确 AI 路径，重新打开该 AI 核验 | 当前窗口标题不能代替磁盘文件回读 |

## TIFF 与颜色

准备脚本针对不透明 RGB 图像，将同样的 RGB 样本写入一个新的、不带原图 ICC 的 TIFF，并验证解码像素完全相等。源图文件保持不动。像素值相等不保证不同色彩管理设置下视觉颜色完全相同；若参考图依赖特殊配置文件，应在 Illustrator 中检查色彩管理，或采用保留配置文件的单独导入路线。

帮助脚本不自动处理透明、CMYK 或多页文件。遇到这类输入，先选择符合用户目标的导入或转换方式，不要默默合并透明度或更改颜色空间。

## 验证边界

原始实例在 Illustrator 29.5.1 中得到 26 处活文字、12 个插画组、1,220 条路径，位图和置入图像均为 0，并检查了 `≥` 的码位 8805。这是一次实际结果，不是新任务应当满足的固定数量。

整理为通用脚本后，2026-09-08 在同版本 macOS Illustrator 中再次完成重建与回读。实时入口分批重建了 1,246 个叶对象（1,220 条路径和 26 个文字对象）；原生导出的实时稿 PNG 与重建稿 PNG 像素完全一致。Windows COM 启动入口仍需要 Windows 实机验证。

同日对插画内标签继续检查并补齐后，最终实例含 40 个原生 TextFrame、12 个插画组、1,197 条路径、零位图；实时创建 1,237 个叶对象，重建稿与实时稿 PNG 仍像素一致。下标使用普通数字文本框按下标位置排版，避免当前字体缺少 Unicode 下标字形。文字背景自动取色排除深色墨迹，修复了紧密小字错误选中黑色的情况。

通用脚本采用上述已验证机制，增加输入、文件存在性和文档状态检查。每次使用仍须在实际 Illustrator 中运行并验收。

Adobe 官方说明：[编辑描摹结果](https://helpx.adobe.com/illustrator/desktop/manage-objects/traces-mockups-symbols/edit-image-trace-results.html)、[图像描摹面板选项](https://helpx.adobe.com/uk/illustrator/desktop/manage-objects/traces-mockups-symbols/image-trace-panel-options.html)。脚本接口细节优先检查实际安装版本的脚本字典和对象反射。
