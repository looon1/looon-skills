# Private SuperSVG runtime

Read this reference only when deploying, refreshing, diagnosing, or smoke-testing the private SuperSVG server.

## What is bundled

The Skill bundles only integration code:

- `scripts/deploy_supersvg.py`: cross-platform SSH deployment and verification entrypoint.
- `server/supersvg_tiled.py`: aspect-preserving tiled inference and native SVG clipping.
- `server/supersvg_asset_batch.py`: one model load for all complex crops in a figure.
- `server/requirements-supersvg.txt`: inference dependencies other than PyTorch/torchvision and the upstream repository.

It does not redistribute the upstream repository or model weights. Deployment clones the official `sjtuplayer/SuperSVG` repository at pinned revision `6c3d45b435e0cc7ca0de3976d4d1aef6b50111a1` and downloads the public `JTUplayer/SuperSVG` checkpoints.

## Remote layout

Defaults are public-safe placeholders and may be overridden:

- SSH target: `supersvg-server`
- Runtime root: `services/supersvg-eval`, relative to the SSH user's home
- Repository: `<runtime-root>/SuperSVG`
- Python environment: `<runtime-root>/.venv`
- Model weights: `<runtime-root>/SuperSVG/weights/{coarse.pt,refine.pt}`
- Jobs: `<runtime-root>/jobs/<job-id>`
- GPU: physical GPU1 by default; one quality job at a time

Do not put passwords, private keys, access tokens, or signed URLs in this repository or in job manifests. Configure SSH separately in `~/.ssh/config` or pass a `user@host` target.

## Deployment modes

Deployment mutates the remote server and requires explicit user authorization.

### Verify only

This is read-only. It checks SSH, the managed Python environment, upstream inference code, both adapters, both model weights, the selected GPU, CUDA, OpenCV, PyTorch, and pydiffvg.

```bash
python3 scripts/deploy_supersvg.py \
  --mode verify \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --gpu-index 1
```

### Refresh an existing runtime

This uploads only the two bundled adapters, then performs the same strict verification. It does not pull, reset, or replace the upstream repository or Python environment.

```bash
python3 scripts/deploy_supersvg.py \
  --mode adapters \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --gpu-index 1
```

Add `--download-weights` if the public checkpoints need to be restored.

### Bootstrap a new runtime

Bootstrap requires Linux, an NVIDIA GPU, `git`, `cmake`, `nvcc`, `nvidia-smi`, and the selected Python command. It creates a narrow runtime directory, clones the pinned upstream revision only when the repository is absent, creates a virtual environment only when absent, installs dependencies, builds diffvg, downloads both public checkpoints, uploads the adapters, and verifies the final runtime.

```bash
python3 scripts/deploy_supersvg.py \
  --mode bootstrap \
  --ssh-target user@gpu-host \
  --remote-root services/supersvg-eval \
  --remote-python python3.10 \
  --gpu-index 1
```

If the server requires a specific PyTorch wheel index, append for example:

```text
--torch-index-url https://download.pytorch.org/whl/cu121
```

Choose the index that matches the server driver/toolchain; do not copy the example blindly.

## Real smoke test

Verification proves the runtime imports and required files exist. A smoke image additionally proves model loading, GPU inference, checkpoint compatibility, SVG download, XML parsing, non-empty paths, and zero embedded raster nodes.

```bash
python3 scripts/deploy_supersvg.py \
  --mode adapters \
  --ssh-target supersvg-server \
  --remote-root services/supersvg-eval \
  --gpu-index 1 \
  --smoke-image /absolute/path/to/one-complex-object.png \
  --smoke-output /absolute/path/to/supersvg-smoke.svg
```

The smoke test enforces the same quality floor: at least 1,000 paths and 10 refinement iterations. Defaults remain 1,600 and 14. It refuses to start when the selected GPU already has a compute process and never kills unrelated work.

Use `--dry-run` with any mode to print the exact SSH/SCP plan without connecting or changing the server.

## GPU and SAM3 boundary

Check the selected GPU before every real job. If occupied, queue the job or report the conflict. Never terminate an unrelated process.

SAM3 is an independent optional segmentation service. It may generate vector clipping contours around already selected complex objects, but it never performs vectorization. Preserve its pre-run state and never route text, arrows, frames, connectors, or other rule elements through it.

## Capacity and quality

A tested single RTX 3090 24 GB configuration can run the quality profile. Process all complex crops in one model load by default. `--per-asset` exists for recovery only.

- Default crop/tile path count: 1,600; values below 1,000 are rejected.
- Default fine-tuning iterations: 14; values below 10 are rejected.
- Dense crops may increase rows/columns; every tile retains overlap and native clipping.
- Refine batch size may be reduced to fit memory because it does not change the path target or iteration count.

There is no language-model token quota. Quality is controlled by path count, refinement iterations, crop coverage, validation, and visual fidelity.
