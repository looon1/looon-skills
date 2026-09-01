#!/usr/bin/env python3
"""Portable Illustrator流程图绘制 cache preparation and Illustrator playback router."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f"Command failed: {command[0]}")
    return result


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def prepare_cache(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    prepare_script = Path(__file__).with_name("prepare_geometry_cache.py")
    command = [
        sys.executable,
        str(prepare_script),
        "--input", str(args.input_svg.resolve(strict=True)),
        "--output-dir", str(work_dir),
        "--job-id", args.job_id or args.input_svg.stem,
        "--min-batch-size", str(args.min_batch_size),
        "--max-batch-size", str(args.max_batch_size),
        "--complex-point-threshold", str(args.complex_point_threshold),
        "--max-batch-points", str(args.max_batch_points),
    ]
    run_checked(command)
    cache_path = work_dir / "geometry-cache.json"
    state_path = work_dir / "playback.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8-sig"))
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    return cache, state, cache_path, state_path


def windows_playback(args: argparse.Namespace) -> int:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        raise RuntimeError("PowerShell is required for Illustrator playback on Windows")
    script = Path(__file__).with_name("run_illustrator_flowchart.ps1")
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script),
        "-InputSvg", str(args.input_svg.resolve()),
        "-WorkDir", str(args.work_dir.resolve()),
        "-OutputAi", str(args.output_ai.resolve()),
        "-OutputPng", str(args.output_png.resolve()),
        "-PythonExecutable", sys.executable,
        "-MinBatchSize", str(args.min_batch_size),
        "-MaxBatchSize", str(args.max_batch_size),
        "-ComplexPointThreshold", str(args.complex_point_threshold),
        "-MaxBatchPoints", str(args.max_batch_points),
        "-DelayMs", str(args.delay_ms),
        "-CheckpointSeconds", str(args.checkpoint_seconds),
        "-Placement", args.placement,
        "-MaxWidthFraction", str(args.max_width_fraction),
        "-MaxHeightFraction", str(args.max_height_fraction),
    ]
    result = subprocess.run(command)
    return int(result.returncode)


class MacIllustratorBridge:
    APP_ID = "com.adobe.illustrator"

    def __init__(self, runtime_path: Path, scratch_dir: Path) -> None:
        if not shutil.which("osascript"):
            raise RuntimeError("osascript is required for Illustrator playback on macOS")
        process_check = subprocess.run(["pgrep", "-f", "Adobe Illustrator"], capture_output=True)
        if process_check.returncode != 0:
            raise RuntimeError("AI_NOT_RUNNING|Open Illustrator and the target document before drawing")
        self.runtime_path = runtime_path.resolve()
        self.scratch_dir = scratch_dir
        self.counter = 0

    def run_source(self, source: str) -> str:
        self.counter += 1
        jsx_path = self.scratch_dir / f"bridge-{self.counter:04d}.jsx"
        jsx_path.write_text(source, encoding="utf-8")
        apple_script = """
on run argv
  set jsxFile to POSIX file (item 1 of argv)
  with timeout of 3600 seconds
    tell application id "com.adobe.illustrator"
      return do javascript jsxFile
    end tell
  end timeout
end run
"""
        result = run_checked(["osascript", "-e", apple_script, str(jsx_path)])
        return result.stdout.strip()

    def run_operation(self, configuration: dict[str, Any]) -> str:
        config = json.dumps(configuration, ensure_ascii=False, separators=(",", ":"))
        runtime = json.dumps(self.runtime_path.as_posix())
        return self.run_source(
            f"var ILLUSTRATOR_FLOWCHART_CACHED_CONFIG={config};\n$.evalFile(new File({runtime}));\n"
        )


def result_value(result: str, key: str) -> str | None:
    for part in result.split("|"):
        if part.startswith(key + "="):
            return part[len(key) + 1 :]
    return None


def macos_qa_source(document_name: str, root_group_name: str, expectations: list[dict[str, Any]]) -> str:
    config = json.dumps(
        {"documentName": document_name, "rootGroupName": root_group_name, "batches": expectations},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""
(function(){{
  var c={config};
  function namedGroup(container,name){{
    for(var i=0;i<container.groupItems.length;i+=1){{
      try{{var item=container.groupItems[i];if(item&&item.name===name){{return item;}}}}catch(ignore){{}}
    }}
    return null;
  }}
  function namedArtwork(container,name){{
    var group=namedGroup(container,name);if(group!==null){{return group;}}
    var collections=[container.pathItems,container.compoundPathItems,container.textFrames];
    for(var q=0;q<collections.length;q+=1){{
      for(var i=0;i<collections[q].length;i+=1){{
        try{{var item=collections[q][i];if(item&&item.name===name){{return item;}}}}catch(ignore){{}}
      }}
    }}
    return null;
  }}
  var doc=null;
  for(var d=0;d<app.documents.length;d+=1){{if(app.documents[d].name===c.documentName){{doc=app.documents[d];break;}}}}
  if(doc===null){{return 'ERROR|TARGET_DOCUMENT_MISSING';}}
  var root=namedGroup(doc,c.rootGroupName);
  if(root===null){{return 'ERROR|ROOT_GROUP_MISSING';}}
  var missing=0;
  for(var b=0;b<c.batches.length;b+=1){{
    var batch=namedGroup(root,c.batches[b].groupName);
    if(batch===null){{missing+=c.batches[b].paintNames.length;continue;}}
    for(var a=0;a<c.batches[b].paintNames.length;a+=1){{
      if(namedArtwork(batch,c.batches[b].paintNames[a])===null){{missing+=1;}}
    }}
  }}
  return 'OK|missing='+missing+'|placed='+root.placedItems.length+'|raster='+root.rasterItems.length;
}}());
"""


def macos_playback(args: argparse.Namespace, cache: dict[str, Any], state: dict[str, Any], state_path: Path) -> int:
    runtime_path = Path(__file__).with_name("illustrator_flowchart_cached_runtime.jsx")
    args.output_ai.parent.mkdir(parents=True, exist_ok=True)
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="illustrator-flowchart-macos-") as temporary:
        scratch = Path(temporary)
        bridge = MacIllustratorBridge(runtime_path, scratch)
        info = bridge.run_source(
            '(app.documents.length<1)?"ERROR|AI_DOCUMENT_REQUIRED":"OK|documentName="+app.activeDocument.name;'
        )
        if not info.startswith("OK|"):
            raise RuntimeError(info)
        document_name = result_value(info, "documentName") or ""
        batch_payload_path = scratch / "current-batch.json"
        last_checkpoint = time.monotonic()
        batches_since_checkpoint = 0
        for batch_state in state["batches"]:
            atoms = [cache["atoms"][int(index)] for index in batch_state["atom_indices"]]
            batch_payload_path.write_text(
                json.dumps(
                    {"viewBox": cache["view_box"], "atoms": atoms, "clip": batch_state.get("clip")},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            configuration = {
                "operation": "draw",
                "batchJsonPath": batch_payload_path.as_posix(),
                "targetDocumentName": document_name,
                "rootGroupName": state["root_group_name"],
                "batchGroupName": batch_state["group_name"],
                "placement": args.placement,
                "maxWidthFraction": args.max_width_fraction,
                "maxHeightFraction": args.max_height_fraction,
                "delayMs": args.delay_ms,
                "targetLayerName": args.target_layer_name,
            }
            result = ""
            for _ in range(args.retry_limit):
                batch_state["attempts"] = int(batch_state.get("attempts", 0)) + 1
                write_json_atomic(state_path, state)
                result = bridge.run_operation(configuration)
                if result.startswith("OK|"):
                    break
                batch_state["last_error"] = result
                write_json_atomic(state_path, state)
                time.sleep(0.1)
            if not result.startswith("OK|"):
                raise RuntimeError(f"RESUME_REQUIRED|batch={batch_state['index']}|{result}")
            batch_state["completed"] = True
            batch_state["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            batch_state["last_error"] = None
            write_json_atomic(state_path, state)
            created_in_batch = int(result_value(result, "created") or "0")
            if created_in_batch > 0:
                batches_since_checkpoint += 1
            checkpoint_due = (
                batches_since_checkpoint > 0
                and (
                    batches_since_checkpoint >= args.checkpoint_batches
                    or time.monotonic() - last_checkpoint >= args.checkpoint_seconds
                )
            )
            if checkpoint_due:
                save = bridge.run_operation({
                    "operation": "save",
                    "targetDocumentName": document_name,
                    "outputAi": args.output_ai.resolve().as_posix(),
                })
                if not save.startswith("OK|"):
                    raise RuntimeError(f"AI checkpoint failed: {save}")
                document_name = result_value(save, "documentName") or document_name
                batches_since_checkpoint = 0
                last_checkpoint = time.monotonic()

        expectations: list[dict[str, Any]] = []
        for batch_state in state["batches"]:
            names: list[str] = []
            for atom_index in batch_state["atom_indices"]:
                atom = cache["atoms"][int(atom_index)]
                parts = atom.get("paintParts", [])
                if len(parts) <= 1:
                    names.append(atom["objectName"])
                else:
                    names.extend(f"{atom['objectName']}_P{index}" for index in range(len(parts)))
            expectations.append({"groupName": batch_state["group_name"], "paintNames": names})
        qa = bridge.run_source(macos_qa_source(document_name, state["root_group_name"], expectations))
        if not qa.startswith("OK|missing=0|placed=0|raster=0"):
            raise RuntimeError(f"QA_FAILED|{qa}")
        final_save = bridge.run_operation({
            "operation": "save",
            "targetDocumentName": document_name,
            "outputAi": args.output_ai.resolve().as_posix(),
        })
        if not final_save.startswith("OK|"):
            raise RuntimeError(f"Final AI save failed: {final_save}")
        document_name = result_value(final_save, "documentName") or document_name
        exported = bridge.run_operation({
            "operation": "export",
            "targetDocumentName": document_name,
            "outputPng": args.output_png.resolve().as_posix(),
        })
        if not exported.startswith("OK|"):
            raise RuntimeError(f"Final PNG export failed: {exported}")
    if not args.output_ai.exists() or not args.output_png.exists():
        raise RuntimeError("QA_FAILED|Expected AI or PNG output is missing")
    print(json.dumps({
        "ok": True,
        "platform": "macos",
        "ai": str(args.output_ai.resolve()),
        "png": str(args.output_png.resolve()),
        "batches": len(state["batches"]),
    }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-svg", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--output-ai", type=Path)
    parser.add_argument("--output-png", type=Path)
    parser.add_argument("--job-id")
    parser.add_argument("--min-batch-size", type=int, default=20)
    parser.add_argument("--max-batch-size", type=int, default=50)
    parser.add_argument("--complex-point-threshold", type=int, default=320)
    parser.add_argument("--max-batch-points", type=int, default=2200)
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--placement", default="center", choices=[
        "center", "top-center", "left-center", "bottom-center",
        "bottom-right", "top-right", "bottom-left", "top-left",
    ])
    parser.add_argument("--max-width-fraction", type=float, default=0.72)
    parser.add_argument("--max-height-fraction", type=float, default=0.78)
    parser.add_argument("--target-layer-name", default="")
    parser.add_argument("--retry-limit", type=int, default=12)
    parser.add_argument("--checkpoint-batches", type=int, default=10)
    parser.add_argument("--checkpoint-seconds", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-illustrator", action="store_true")
    args = parser.parse_args()
    stem = args.input_svg.stem
    args.output_ai = (args.output_ai or args.input_svg.with_name(stem + ".ai")).resolve()
    args.output_png = (args.output_png or args.input_svg.with_name(stem + ".png")).resolve()
    if not 1 <= args.min_batch_size <= args.max_batch_size <= 50:
        parser.error("batch sizes must satisfy 1 <= min <= max <= 50")
    if args.checkpoint_batches < 1 or args.checkpoint_seconds < 5:
        parser.error("checkpoint-batches must be >= 1 and checkpoint-seconds must be >= 5")
    cache, state, cache_path, state_path = prepare_cache(args)
    system = platform.system().lower()
    if args.dry_run or args.no_illustrator or system == "linux":
        print(json.dumps({
            "ok": True,
            "mode": "core-only" if not args.dry_run else "dry-run",
            "platform": system,
            "cache": str(cache_path),
            "state": str(state_path),
            "atoms": cache["total_atoms"],
            "batches": len(state["batches"]),
            "illustrator_untouched": True,
        }, ensure_ascii=False))
        return 0
    if system == "windows":
        return windows_playback(args)
    if system == "darwin":
        return macos_playback(args, cache, state, state_path)
    raise RuntimeError(f"Unsupported platform: {platform.system()}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ILLUSTRATOR_FLOWCHART_RUN_ERROR|{exc}", file=sys.stderr)
        raise SystemExit(1)
