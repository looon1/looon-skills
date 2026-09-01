#!/usr/bin/env python3
"""Run the private SuperSVG quality pipeline through SSH and download its SVG."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--ssh-target", default="supersvg-server")
    parser.add_argument("--remote-root", default="services/supersvg-eval")
    parser.add_argument("--gpu-index", type=int, default=1)
    parser.add_argument("--rows", type=int, default=1)
    parser.add_argument("--cols", type=int, default=1)
    parser.add_argument("--overlap", type=int, default=64)
    parser.add_argument("--path-num", type=int, default=1600)
    parser.add_argument("--optimize-iter", type=int, default=14)
    parser.add_argument("--refine-batch-size", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=7200)
    args = parser.parse_args()

    for executable in ("ssh", "scp"):
        if not shutil.which(executable):
            raise RuntimeError(f"{executable} is required for private SuperSVG execution")
    if args.path_num < 1000 or args.optimize_iter < 10:
        parser.error("quality mode requires path-num >= 1000 and optimize-iter >= 10")
    if args.rows < 1 or args.cols < 1 or args.overlap < 0:
        parser.error("invalid tiling settings")

    input_path = args.input.resolve(strict=True)
    output_path = args.output.resolve()
    state_path = args.state.resolve()
    input_hash = sha256(input_path)
    state: dict[str, Any] = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if state.get("input_sha256") != input_hash:
            raise RuntimeError("Existing SuperSVG state belongs to a different input image")
    if state.get("status") == "completed" and output_path.exists():
        print(json.dumps(state, ensure_ascii=False))
        return 0

    job_id = state.get("job_id") or f"illustrator-flowchart-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    remote_root = args.remote_root.rstrip("/")
    remote_job = f"{remote_root}/jobs/{job_id}"
    remote_input = f"{remote_job}/source{input_path.suffix.lower()}"
    remote_output_dir = f"{remote_job}/output"
    remote_svg = f"{remote_output_dir}/source-supersvg-tiled.svg"
    state.update({
        "schema_version": "1.0",
        "provider": "supersvg",
        "model": "JTUplayer/SuperSVG",
        "quality_mode": True,
        "job_id": job_id,
        "input_sha256": input_hash,
        "remote_job_dir": remote_job,
        "settings": {
            "rows": args.rows,
            "cols": args.cols,
            "overlap": args.overlap,
            "path_num_per_tile": args.path_num,
            "optimize_iter": args.optimize_iter,
            "refine_batch_size": args.refine_batch_size,
            "gpu_index": args.gpu_index,
        },
        "status": "running",
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    write_json_atomic(state_path, state)

    run(["ssh", args.ssh_target, "mkdir -p " + shlex.quote(remote_job)], timeout=60)
    run(["scp", str(input_path), f"{args.ssh_target}:{remote_input}"], timeout=600)
    python_path = f"{remote_root}/.venv/bin/python"
    tiled_script = f"{remote_root}/SuperSVG/supersvg_tiled.py"
    remote_command = " ".join(shlex.quote(part) for part in [
        "env", f"CUDA_VISIBLE_DEVICES={args.gpu_index}", python_path, tiled_script,
        "--input", remote_input,
        "--output-dir", remote_output_dir,
        "--rows", str(args.rows),
        "--cols", str(args.cols),
        "--overlap", str(args.overlap),
        "--path-num", str(args.path_num),
        "--optimize-iter", str(args.optimize_iter),
        "--refine-batch-size", str(args.refine_batch_size),
        "--device", "cuda",
    ])
    try:
        run(["ssh", args.ssh_target, remote_command], timeout=args.timeout)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        run(["scp", f"{args.ssh_target}:{remote_svg}", str(output_path)], timeout=600)
    except Exception as exc:
        state["status"] = "failed"
        state["last_error"] = str(exc)
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_json_atomic(state_path, state)
        raise

    state["status"] = "completed"
    state["output_sha256"] = sha256(output_path)
    state["last_error"] = None
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    write_json_atomic(state_path, state)
    print(json.dumps(state, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"SUPERSVG_REMOTE_ERROR|{exc}", flush=True)
        raise SystemExit(1)
