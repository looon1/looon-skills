# Illustrator流程图绘制

把科研流程图、机制图和技术示意图重建为真正可编辑的 SVG，并在 macOS/Windows 上继续绘制到 Adobe Illustrator。

它不是把整张图片交给模型重新生成。正确的实现是对象分流：文字、线条、箭头、边框、面板背景和基础形状直接创建为原生矢量对象；只有动物、细胞、蛋白纹理、分子插画等复杂图形才裁切后送入私有 SuperSVG。低清或带背景污染的复杂裁片可以先经 ChatGPT 网页客户端重建为高清透明 PNG，再进入 SuperSVG。最终按原层级合成、恢复实时文字、验证 SVG，并生成可恢复的 Illustrator 几何缓存。

## 核心架构

```text
原始图片
  -> Scene Manifest 对象分流
     -> 规则元素：原生 SVG
     -> 复杂对象：裁切
        -> 常规：透明预处理 -> 私有 SuperSVG
        -> 质量升级：ChatGPT 网页重建 -> Alpha/语义审计 -> 私有 SuperSVG
  -> 混合 Master SVG
  -> 实时文字恢复与矢量审计
  -> 无损几何缓存
  -> Illustrator 回放（macOS / Windows，可选）
```

SuperSVG 不处理文字、箭头、连接线、坐标轴、边框或面板。这样既避免模型臆造标签，也避免为了速度牺牲复杂插图细节。

## 支持范围

- 科研工作流、实验流程图、机制图、图形摘要和技术架构图。
- 直接生成实时文字、线条、折线、箭头、圆、椭圆、矩形、区域、线性渐变、虚线和矢量裁切。
- 复杂对象通过自托管 `JTUplayer/SuperSVG` 转换为真实 SVG 路径。
- 可选使用公开 MIT 项目 `leeguooooo/chatgpt-imagegen` 的 `web` 后端，把单个低质复杂对象交给已登录的 ChatGPT 网页生成；不调用 Codex 内置生图，也不需要 `OPENAI_API_KEY`。
- macOS：AppleScript/JSX 续画到已经打开的 Illustrator 文档。
- Windows：PowerShell/COM 续画到 Illustrator。
- Linux：完成 Master SVG 和几何缓存；不虚假声称存在 Illustrator 输出。

## 安装 Skill

将本目录复制到 Codex Skills 目录：

```bash
git clone https://github.com/looon1/looon-skills.git
cp -R looon-skills/skills/illustrator-flowchart-drawing ~/.codex/skills/
cd ~/.codex/skills/illustrator-flowchart-drawing
./setup.sh
```

Windows 使用：

```powershell
./setup.ps1
```

## 可选：ChatGPT 网页高清透明素材层

此层只用于低清、噪声或底色污染严重的复杂对象，不能处理整图、文字、箭头、框、坐标轴、精确化学结构或面板背景。

安装已审计的公开客户端：

```bash
npx skills add leeguooooo/chatgpt-imagegen -g
```

网页后端还需要 `chrome-use`、Chrome 扩展，以及已经登录 `chatgpt.com` 的 Chrome。浏览器桥接属于单独的机器级安装，应在用户明确同意后配置。完成后检查：

```bash
./setup.sh --verify-chatgpt-web
```

生成单个参考素材：

```bash
./scripts/chatgpt_web_image_asset.py \
  --reference /absolute/path/object-source.png \
  --prompt "忠实重建这一个科研插图对象；保持方向、轮廓、颜色、数量和关系；输出真实透明 PNG；不要文字、箭头、边框、背景或额外结构" \
  --output /absolute/path/job/assets/enhanced/object-web.png
```

包装脚本固定使用 `--backend web`，不会自动回退到 Codex、API 或其他模型。网页客户端下载成功后仍会检查 PNG 的真实 Alpha；RGB、全不透明 RGBA、全透明文件和伪棋盘格都会失败。Alpha 通过只代表背景合格，仍需人工/视觉模型核对科学语义后，才能在 Scene Manifest 中标记为 `accepted`。

## 最关键：部署 SuperSVG

模型运行在带 NVIDIA GPU 的 Linux 服务器上，本机通过 SSH/SCP 提交复杂对象。仓库不会上传模型权重、服务器密码或私钥。

先配置一个 SSH 目标，例如：

```sshconfig
Host supersvg-server
  HostName your-gpu-host
  User your-user
  Port 22
  IdentityFile ~/.ssh/id_ed25519
```

已有 SuperSVG 环境时，只更新本 Skill 的两个适配器并严格检查：

```bash
python3 scripts/deploy_supersvg.py \
  --mode adapters \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --gpu-index 1
```

全新服务器可以执行可审计的 bootstrap：

```bash
python3 scripts/deploy_supersvg.py \
  --mode bootstrap \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --remote-python python3.10 \
  --gpu-index 1
```

Bootstrap 会检查 `git/cmake/nvcc/nvidia-smi`，克隆官方 SuperSVG 固定版本，创建隔离环境，安装依赖、编译 diffvg、下载公开权重、上传适配器，然后运行严格健康检查。已有仓库不会被强制 reset 或覆盖。

最后建议用一张只包含复杂对象的小图做真实推理测试：

```bash
python3 scripts/deploy_supersvg.py \
  --mode adapters \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --gpu-index 1 \
  --smoke-image /absolute/path/to/complex-object.png \
  --smoke-output /absolute/path/to/supersvg-smoke.svg
```

Smoke test 会验证模型加载、GPU 推理、权重兼容、SVG 下载、有效路径和零位图节点。GPU 已被其他计算进程占用时会停止，不会杀掉其他任务。

完整部署参数和故障边界见 [references/server-runtime.md](references/server-runtime.md)。

## 输入

每次重建需要：

1. 原始 PNG/JPEG/WebP。
2. Scene Manifest：每个对象的类型、位置、层级和样式；明确区分规则元素与复杂对象。
3. Text Manifest：文字内容、坐标、字体、字号、字重、颜色、旋转、对齐和层级。
4. 输出目录。

字段定义见 [references/manifest-schema.md](references/manifest-schema.md)。Scene Manifest 是强制输入，因此不存在“整图全部送给 SuperSVG”的降级模式。

## 运行

macOS/Linux：

```bash
./scripts/run_from_image.sh \
  --input-image /absolute/path/reference.png \
  --scene-manifest /absolute/path/scene.json \
  --text-manifest /absolute/path/text-manifest.json \
  --output-root /absolute/path/output \
  --ssh-target supersvg-server \
  --supersvg-remote-root services/supersvg-eval
```

Windows：

```powershell
./scripts/run_from_image.ps1 \
  -InputImage C:\path\reference.png \
  -SceneManifest C:\path\scene.json \
  -TextManifest C:\path\text-manifest.json \
  -OutputRoot C:\path\output \
  -SshTarget supersvg-server \
  -SuperSvgRemoteRoot services/supersvg-eval
```

如果只需要 SVG，追加 `--no-illustrator`，Windows 使用 `-NoIllustrator`。

## 质量策略

- 默认每个复杂裁片/瓦片 1,600 条路径、14 次优化。
- 少于 1,000 条路径或 10 次优化会直接拒绝。
- 多个复杂对象默认一次加载模型，减少重复加载但不降低路径数或优化次数。
- 性能优化只能发生在传输、批处理、缓存、重试和检查点；不得简化路径、丢弃渐变、移除裁切或降低输入分辨率。
- SVG 检查会拒绝嵌入位图、脚本、空矢量、无效 XML、未解析复杂资产和外部内容。
- Illustrator 不能无损表达的 SVG 特性会停在 Master SVG，不会静默扁平化。

## 输出

每次运行生成独立的 `illustrator-flowchart-N/`：

- `assets/`：复杂对象裁片、SuperSVG 结果和远程任务状态。
- `assets/enhanced/`：可选 ChatGPT 网页源图及 Alpha/来源审计报告。
- `illustrator-flowchart-N-hybrid-base.svg`：规则元素与复杂对象合成结果。
- `illustrator-flowchart-N.svg`：恢复实时文字后的 Master SVG。
- `.illustrator-flowchart-internal/live-cache/`：可恢复几何缓存和进度。
- `.ai` 与 `.png`：仅在 Illustrator 回放和渲染一致性检查真正通过后产生。

## 已验证结果

真实科研流程图测试曾完成：17 个复杂 SuperSVG 对象、37 个原生规则对象、45 个实时文字、27,330 个矢量元素和 0 个位图节点；Illustrator 缓存 18,925 个原子对象，392/392 批次完成。详细审计见 [AUDIT.md](AUDIT.md)。

## 目录

```text
illustrator-flowchart-drawing/
├── SKILL.md
├── README.md
├── doctor.py
├── setup.sh / setup.ps1
├── scripts/
│   ├── deploy_supersvg.py
│   ├── chatgpt_web_image_asset.py
│   ├── run_from_image.py
│   ├── vectorize_scene_assets.py
│   └── run_illustrator_flowchart.py
├── server/
│   ├── supersvg_tiled.py
│   ├── supersvg_asset_batch.py
│   └── requirements-supersvg.txt
└── references/
```

## 上游项目

- SuperSVG official repository: <https://github.com/sjtuplayer/SuperSVG>
- Model weights: <https://huggingface.co/JTUplayer/SuperSVG>
- Paper: *SuperSVG: Superpixel-based Scalable Vector Graphics Synthesis*, CVPR 2024
- ChatGPT web client: <https://github.com/leeguooooo/chatgpt-imagegen>

本 Skill 只提供对象分流、服务器部署适配、质量闸门、混合 SVG、缓存和 Illustrator 回放逻辑；SuperSVG 上游代码及权重遵循各自项目的许可。
