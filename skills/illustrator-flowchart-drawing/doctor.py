#!/usr/bin/env python3
"""Read-only environment diagnostic for the SuperSVG-only Illustrator流程图绘制 package."""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


SUPERSVG_REVISION = "6c3d45b435e0cc7ca0de3976d4d1aef6b50111a1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-server", action="store_true")
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--remote-root", default="services/supersvg-eval")
    parser.add_argument("--gpu-index", type=int, default=1)
    args = parser.parse_args()

    if args.ssh_target.startswith("-") or not args.ssh_target.strip():
        parser.error("invalid SSH target")

    root = Path(__file__).resolve().parent
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str, required: bool = True) -> None:
        checks.append({"name": name, "ok": ok, "required": required, "detail": detail})

    record("python", sys.version_info >= (3, 10), platform.python_version())
    for module in ("fontTools", "PIL"):
        record(f"python_module:{module}", importlib.util.find_spec(module) is not None, "available" if importlib.util.find_spec(module) else "missing")
    for executable in ("ssh", "scp"):
        found = shutil.which(executable)
        record(f"executable:{executable}", found is not None, found or "missing")
    for relative in (
        "scripts/run_from_image.py",
        "scripts/deploy_supersvg.py",
        "scripts/vectorize_scene_assets.py",
        "scripts/build_hybrid_master.py",
        "scripts/prepare_geometry_cache.py",
        "scripts/illustrator_flowchart_cached_runtime.jsx",
        "server/supersvg_tiled.py",
        "server/supersvg_asset_batch.py",
    ):
        path = root / relative
        record(f"package_file:{relative}", path.is_file(), str(path))
    magick = shutil.which("magick") or shutil.which("convert")
    record("optional:imagemagick", magick is not None, magick or "needed only for SAM3 masks and render-equivalence QA", required=False)

    if args.verify_server:
        if not shutil.which("ssh"):
            record("server", False, "ssh is unavailable")
        else:
            remote = args.remote_root.rstrip("/")
            quoted_remote = shlex.quote(remote)
            python_code = shlex.quote(
                "import cv2, pydiffvg, torch; "
                "assert torch.cuda.is_available(), 'CUDA unavailable'; "
                "print(torch.cuda.get_device_name(0))"
            )
            remote_command = (
                f"test -x {quoted_remote}/.venv/bin/python && "
                f"test -f {quoted_remote}/SuperSVG/inference.py && "
                f"test -f {quoted_remote}/SuperSVG/supersvg_tiled.py && "
                f"test -f {quoted_remote}/SuperSVG/supersvg_asset_batch.py && "
                f"test -f {quoted_remote}/SuperSVG/weights/coarse.pt && "
                f"test -f {quoted_remote}/SuperSVG/weights/refine.pt && "
                f"test \"$(git -C {quoted_remote}/SuperSVG rev-parse HEAD)\" = {SUPERSVG_REVISION} && "
                f"nvidia-smi -i {args.gpu_index} >/dev/null && "
                f"env CUDA_VISIBLE_DEVICES={args.gpu_index} {quoted_remote}/.venv/bin/python -c {python_code}"
            )
            result = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", args.ssh_target, remote_command],
                text=True, capture_output=True, timeout=20,
            )
            detail = "ready" if result.returncode == 0 else (result.stderr.strip() or "required remote files are missing")
            record("server", result.returncode == 0, detail)

    failed = [item for item in checks if item["required"] and not item["ok"]]
    report = {
        "ok": not failed,
        "package": "illustrator-flowchart-drawing",
        "version": (root / "VERSION").read_text(encoding="utf-8").strip() if (root / "VERSION").is_file() else None,
        "platform": platform.system().lower(),
        "python": sys.executable,
        "checks": checks,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
