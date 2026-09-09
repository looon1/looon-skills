#!/usr/bin/env python3
"""Run Illustrator JSX through its native AppleScript interface, yielding between live batches."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote

APPLESCRIPT = '''on run argv
    set scriptFile to POSIX file (item 1 of argv)
    tell application id "com.adobe.illustrator"
        if item 2 of argv is "activate" then activate
        with timeout of 240 seconds
            do javascript scriptFile
        end timeout
    end tell
end run
'''


def execute(script, activate=False):
    subprocess.run(['osascript', '-', str(script), 'activate' if activate else 'keep'],
                   input=APPLESCRIPT, text=True, check=True, timeout=270,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run(job, stage):
    if sys.platform != 'darwin':
        raise RuntimeError('This launcher requires macOS with desktop Illustrator.')
    log = job / (stage + '.log')
    plan = job / 'live-plan.txt'
    execute(job / (stage + '.jsx'), activate=True)
    if not log.exists():
        raise RuntimeError('Illustrator did not write its stage log.')
    result = log.read_text(encoding='utf-8')
    if 'ERROR:' in result:
        raise RuntimeError('Stage failed; inspect ' + str(log))
    if stage != 'live':
        if result.splitlines()[-1] != 'DONE':
            raise RuntimeError('Stage is incomplete; inspect ' + str(log))
        print(result)
        return
    files = [Path(unquote(p)) for p in plan.read_text(encoding='utf-8').splitlines()]
    command, cursor = job / 'live-command.txt', job / 'live-cursor.txt'
    print('Ready. Click Start / Resume in Illustrator. Ctrl+C pauses the runner.', flush=True)
    try:
        while True:
            index = int(cursor.read_text().strip())
            if index == len(files):
                if 'DONE' not in log.read_text(encoding='utf-8').splitlines():
                    raise RuntimeError('Cursor reached the end without DONE.')
                print('DONE', flush=True)
                return
            mode = command.read_text().strip()
            if mode == 'stop':
                print('Stopped; partial Illustrator document remains open.', flush=True)
                return
            if mode not in ('play', 'step'):
                time.sleep(0.1)
                continue
            if mode == 'step':
                command.write_text('pause')
            execute(files[index])
            if int(cursor.read_text().strip()) != index + 1:
                raise RuntimeError('Batch did not complete; do not retry partial batches.')
            print(f'Batch {index + 1}/{len(files)}', flush=True)
            # This wait is OUTSIDE Illustrator: its event loop is free to paint and handle input.
            time.sleep(0.5)
    except KeyboardInterrupt:
        command.write_text('pause')
        print('Paused. Check the cursor before resuming; never close user documents.', flush=True)
    except Exception:
        command.write_text('pause')
        with log.open('a', encoding='utf-8') as handle:
            handle.write('\nERROR: External runner stopped; inspect the command error before retrying.\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-dir', required=True, type=Path)
    parser.add_argument('--stage', required=True, choices=['inspect', 'trace', 'rebuild', 'structure', 'verify', 'live'])
    args = parser.parse_args()
    try:
        run(args.job_dir.resolve(), args.stage)
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.strip())
