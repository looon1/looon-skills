#!/usr/bin/env python3
"""Deploy, refresh, verify, or smoke-test the private SuperSVG runtime over SSH."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


UPSTREAM_REPOSITORY = "https://github.com/sjtuplayer/SuperSVG.git"
UPSTREAM_REVISION = "6c3d45b435e0cc7ca0de3976d4d1aef6b50111a1"
REMOTE_ROOT_RE = re.compile(r"^/?[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")


class Runner:
    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self.commands: list[list[str]] = []

    def run(self, command: list[str], timeout: int) -> subprocess.CompletedProcess[str] | None:
        self.commands.append(command)
        if self.dry_run:
            print("DRY_RUN|" + shlex.join(command))
            return None
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
        return result


def remote_path(root: str, suffix: str) -> str:
    return root.rstrip("/") + "/" + suffix.lstrip("/")


def ssh(runner: Runner, target: str, command: str, timeout: int = 120) -> subprocess.CompletedProcess[str] | None:
    return runner.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", target, command],
        timeout=timeout,
    )


def scp(runner: Runner, source: Path, target: str, destination: str, timeout: int = 600) -> None:
    runner.run(["scp", str(source), f"{target}:{destination}"], timeout=timeout)


def validate_local_svg(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    counts: dict[str, int] = {"path": 0, "image": 0}
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1]
        if name in counts:
            counts[name] += 1
    if counts["path"] < 1 or counts["image"]:
        raise RuntimeError(f"Invalid smoke SVG: paths={counts['path']} raster_images={counts['image']}")
    return counts


def verify_command(remote_root: str, gpu_index: int, revision: str) -> str:
    root = remote_root.rstrip("/")
    repository = remote_path(root, "SuperSVG")
    python = remote_path(root, ".venv/bin/python")
    python_code = (
        "import cv2, pydiffvg, torch; "
        "assert torch.cuda.is_available(), 'CUDA unavailable'; "
        "print(torch.cuda.get_device_name(0))"
    )
    checks = [
        f"test -x {shlex.quote(python)}",
        f"test -f {shlex.quote(remote_path(repository, 'inference.py'))}",
        f"test -f {shlex.quote(remote_path(repository, 'supersvg_tiled.py'))}",
        f"test -f {shlex.quote(remote_path(repository, 'supersvg_asset_batch.py'))}",
        f"test -f {shlex.quote(remote_path(repository, 'weights/coarse.pt'))}",
        f"test -f {shlex.quote(remote_path(repository, 'weights/refine.pt'))}",
        f"test \"$(git -C {shlex.quote(repository)} rev-parse HEAD)\" = {shlex.quote(revision)}",
        f"nvidia-smi -i {gpu_index} >/dev/null",
        f"env CUDA_VISIBLE_DEVICES={gpu_index} {shlex.quote(python)} -c {shlex.quote(python_code)}",
    ]
    return "set -eu; " + " && ".join(checks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("verify", "adapters", "bootstrap"), default="adapters")
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--remote-root", default="services/supersvg-eval")
    parser.add_argument("--remote-python", default="python3")
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--repository", default=UPSTREAM_REPOSITORY)
    parser.add_argument("--revision", default=UPSTREAM_REVISION)
    parser.add_argument("--torch-index-url")
    parser.add_argument("--download-weights", action="store_true")
    parser.add_argument("--smoke-image", type=Path)
    parser.add_argument("--smoke-output", type=Path)
    parser.add_argument("--path-num", type=int, default=1600)
    parser.add_argument("--optimize-iter", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.ssh_target.startswith("-") or not args.ssh_target.strip():
        parser.error("invalid SSH target")
    root_parts = [part for part in args.remote_root.strip("/").split("/") if part]
    if (
        args.remote_root.strip() in {"", "/", "~"}
        or not REMOTE_ROOT_RE.fullmatch(args.remote_root)
        or any(part in {".", ".."} for part in root_parts)
    ):
        parser.error("remote root must be a narrow relative or absolute directory")
    if args.gpu_index < 0:
        parser.error("GPU index must be non-negative")
    if args.path_num < 1000 or args.optimize_iter < 10:
        parser.error("quality smoke test requires path-num >= 1000 and optimize-iter >= 10")
    if args.smoke_image:
        args.smoke_image = args.smoke_image.resolve(strict=True)
    if args.smoke_output and not args.smoke_image:
        parser.error("--smoke-output requires --smoke-image")
    for executable in ("ssh", "scp"):
        if not shutil.which(executable):
            raise RuntimeError(f"{executable} is required")

    skill_root = Path(__file__).resolve().parent.parent
    server_dir = skill_root / "server"
    adapters = [server_dir / "supersvg_tiled.py", server_dir / "supersvg_asset_batch.py"]
    requirements = server_dir / "requirements-supersvg.txt"
    for file in [*adapters, requirements]:
        if not file.is_file():
            raise FileNotFoundError(file)

    runner = Runner(args.dry_run)
    root = args.remote_root.rstrip("/")
    repository = remote_path(root, "SuperSVG")
    python = remote_path(root, ".venv/bin/python")

    if args.mode == "bootstrap":
        bootstrap_preflight = "set -eu; " + "; ".join([
            "command -v git >/dev/null",
            "command -v cmake >/dev/null",
            "command -v nvcc >/dev/null",
            "command -v nvidia-smi >/dev/null",
            f"command -v {shlex.quote(args.remote_python)} >/dev/null",
        ])
        ssh(runner, args.ssh_target, bootstrap_preflight)
        bootstrap = "set -eu; " + " ".join([
            f"mkdir -p {shlex.quote(root)};",
            f"if [ -e {shlex.quote(repository)} ] && [ ! -d {shlex.quote(remote_path(repository, '.git'))} ]; then",
            "echo 'SUPERSVG_REPOSITORY_CONFLICT|Existing path is not a git repository' >&2; exit 3;",
            f"elif [ ! -d {shlex.quote(remote_path(repository, '.git'))} ]; then",
            f"git clone {shlex.quote(args.repository)} {shlex.quote(repository)};",
            f"git -C {shlex.quote(repository)} checkout --detach {shlex.quote(args.revision)};",
            "else",
            f"test -f {shlex.quote(remote_path(repository, 'inference.py'))};",
            "fi;",
            f"if [ ! -x {shlex.quote(python)} ]; then {shlex.quote(args.remote_python)} -m venv {shlex.quote(remote_path(root, '.venv'))}; fi",
        ])
        ssh(runner, args.ssh_target, bootstrap, timeout=900)
        scp(runner, requirements, args.ssh_target, remote_path(root, "requirements-supersvg.txt"))
        install_parts = [
            "set -eu",
            f"{shlex.quote(python)} -m pip install --upgrade pip setuptools wheel",
        ]
        torch_command = f"{shlex.quote(python)} -m pip install torch torchvision"
        if args.torch_index_url:
            torch_command += " --index-url " + shlex.quote(args.torch_index_url)
        install_parts.extend([
            torch_command,
            f"{shlex.quote(python)} -m pip install -r {shlex.quote(remote_path(root, 'requirements-supersvg.txt'))}",
            f"git -C {shlex.quote(repository)} submodule update --init --recursive",
            f"{shlex.quote(python)} -m pip install -e {shlex.quote(remote_path(repository, 'diffvg'))}",
        ])
        ssh(runner, args.ssh_target, "; ".join(install_parts), timeout=3600)

    if args.mode in {"bootstrap", "adapters"}:
        ssh(
            runner,
            args.ssh_target,
            f"test -d {shlex.quote(repository)} && test -f {shlex.quote(remote_path(repository, 'inference.py'))}",
        )
        for adapter in adapters:
            scp(runner, adapter, args.ssh_target, remote_path(repository, adapter.name))

    if args.download_weights or args.mode == "bootstrap":
        weights_dir = remote_path(repository, "weights")
        download_code = (
            "from huggingface_hub import hf_hub_download; "
            f"[hf_hub_download(repo_id='JTUplayer/SuperSVG', filename=n, local_dir={weights_dir!r}) "
            "for n in ('coarse.pt','refine.pt')]"
        )
        ssh(
            runner,
            args.ssh_target,
            f"mkdir -p {shlex.quote(weights_dir)} && {shlex.quote(python)} -c {shlex.quote(download_code)}",
            timeout=1800,
        )

    verify = ssh(runner, args.ssh_target, verify_command(root, args.gpu_index, args.revision), timeout=180)
    smoke_result = None
    if args.smoke_image:
        gpu_idle_check = (
            "set -eu; "
            f"busy=$(nvidia-smi -i {args.gpu_index} --query-compute-apps=pid --format=csv,noheader,nounits | "
            "tr -d '[:space:]'); "
            "if [ -n \"$busy\" ]; then echo GPU_BUSY:$busy >&2; exit 42; fi"
        )
        ssh(runner, args.ssh_target, gpu_idle_check)
        smoke_root = remote_path(root, "deployment-smoke")
        remote_input = remote_path(smoke_root, "input" + args.smoke_image.suffix.lower())
        remote_output = remote_path(smoke_root, "output")
        ssh(runner, args.ssh_target, f"mkdir -p {shlex.quote(remote_output)}")
        scp(runner, args.smoke_image, args.ssh_target, remote_input)
        command = " ".join(shlex.quote(part) for part in [
            "env", f"CUDA_VISIBLE_DEVICES={args.gpu_index}", python,
            remote_path(repository, "supersvg_tiled.py"),
            "--input", remote_input,
            "--output-dir", remote_output,
            "--rows", "1", "--cols", "1", "--overlap", "64",
            "--path-num", str(args.path_num),
            "--optimize-iter", str(args.optimize_iter),
            "--refine-batch-size", "8", "--device", "cuda",
        ])
        ssh(runner, args.ssh_target, command, timeout=7200)
        remote_svg = remote_path(remote_output, "input-supersvg-tiled.svg")
        local_svg = (args.smoke_output or args.smoke_image.with_name(args.smoke_image.stem + "-supersvg-smoke.svg")).resolve()
        local_svg.parent.mkdir(parents=True, exist_ok=True)
        runner.run(["scp", f"{args.ssh_target}:{remote_svg}", str(local_svg)], timeout=600)
        if not args.dry_run:
            smoke_result = {"output": str(local_svg), **validate_local_svg(local_svg)}

    report = {
        "ok": True,
        "mode": args.mode,
        "dry_run": args.dry_run,
        "ssh_target": args.ssh_target,
        "remote_root": root,
        "repository": args.repository,
        "revision": args.revision,
        "gpu_index": args.gpu_index,
        "verified": verify is not None or args.dry_run,
        "smoke_test": smoke_result,
        "command_count": len(runner.commands),
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SUPERSVG_DEPLOY_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
