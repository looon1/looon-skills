#!/usr/bin/env python3
"""Generate one reference-guided asset through ChatGPT web and enforce real PNG alpha."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


_SKILL_ROOT = Path(__file__).resolve().parents[1]
_MANAGED_PYTHON = (
    _SKILL_ROOT / ".venv" / "Scripts" / "python.exe"
    if os.name == "nt"
    else _SKILL_ROOT / ".venv" / "bin" / "python"
)
if importlib.util.find_spec("PIL") is None and _MANAGED_PYTHON.is_file():
    os.execv(str(_MANAGED_PYTHON), [str(_MANAGED_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

from PIL import Image


CLIENT_REPOSITORY = "leeguooooo/chatgpt-imagegen"


def locate_client(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(explicit.expanduser())
    configured = os.environ.get("CHATGPT_IMAGEGEN_CLI")
    if configured:
        candidates.append(Path(configured).expanduser())
    on_path = shutil.which("chatgpt-imagegen")
    if on_path:
        candidates.append(Path(on_path))
    candidates.append(Path.home() / ".codex" / "skills" / "chatgpt-imagegen" / "chatgpt-imagegen")
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
    raise FileNotFoundError(
        "chatgpt-imagegen client not found; install leeguooooo/chatgpt-imagegen, "
        "then set CHATGPT_IMAGEGEN_CLI if it is outside the standard locations"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--profile", default="auto")
    parser.add_argument("--web-model", default="Instant,Auto")
    parser.add_argument("--project", default="illustrator-flowchart-assets")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    reference = args.reference.expanduser().resolve(strict=True)
    output = args.output.expanduser().resolve()
    report = (args.report.expanduser().resolve() if args.report else output.with_suffix(".chatgpt-web.json"))
    if output.suffix.lower() != ".png":
        parser.error("--output must use .png because alpha validation is mandatory")
    if output.exists() and not args.force:
        parser.error(f"refusing to overwrite existing output: {output}")
    if args.timeout < 30:
        parser.error("--timeout must be at least 30 seconds")

    client = locate_client(args.client)
    version_result = subprocess.run([str(client), "--version"], text=True, capture_output=True, timeout=20)
    client_version = version_result.stdout.strip() or version_result.stderr.strip() or "unknown"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(client), args.prompt,
        "--backend", "web",
        "--no-style",
        "--format", "png",
        "--ref", str(reference),
        "--ref-role", "subject",
        "--out", str(output),
        "--profile", args.profile,
        "--web-model", args.web_model,
        "--project", args.project,
        "--timeout", str(args.timeout),
        "--stall-timeout", "0",
    ]
    environment = dict(os.environ)
    environment["CHATGPT_IMAGEGEN_NO_UPDATE_CHECK"] = "1"
    environment["CHATGPT_IMAGEGEN_NO_AUTO_UPDATE"] = "1"
    run = subprocess.run(
        command, text=True, capture_output=True, timeout=args.timeout + 60, env=environment
    )
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "provider": "chatgpt-web-imagegen",
        "mode": "web",
        "client": CLIENT_REPOSITORY,
        "client_path": str(client),
        "client_version": client_version,
        "reference": str(reference),
        "prompt_record": args.prompt,
        "generated_png": str(output),
        "backend_fallback_allowed": False,
        "returncode": run.returncode,
        "stderr_tail": run.stderr[-4000:],
        "alpha_audit": "FAIL",
        "semantic_audit": "pending",
    }
    if run.returncode != 0 or not output.is_file():
        payload["error"] = "ChatGPT web generation failed or produced no file"
        write_report(report, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    try:
        with Image.open(output) as opened:
            payload["format"] = opened.format
            payload["size"] = list(opened.size)
            payload["bands"] = list(opened.getbands())
            if opened.format != "PNG":
                raise ValueError("downloaded file is not PNG")
            if "A" not in opened.getbands():
                raise ValueError("PNG has no alpha channel")
            alpha_min, alpha_max = opened.convert("RGBA").getchannel("A").getextrema()
            payload["alpha_extrema"] = [alpha_min, alpha_max]
            if alpha_min >= 255:
                raise ValueError("PNG alpha is fully opaque")
            if alpha_max <= 0:
                raise ValueError("PNG is fully transparent")
    except Exception as exc:
        payload["error"] = str(exc)
        payload["sha256"] = sha256(output)
        write_report(report, payload)
        print(json.dumps(payload, ensure_ascii=False))
        return 2

    payload["alpha_audit"] = "PASS"
    payload["transparent_rgba"] = True
    payload["sha256"] = sha256(output)
    write_report(report, payload)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
