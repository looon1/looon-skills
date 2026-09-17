#!/usr/bin/env python3
"""Install locked Python dependencies in this Skill's isolated environment."""
import argparse
from pathlib import Path
import subprocess
import sys
import venv

root=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--formulas',action='store_true',help='Also diagnose installed TeX Live and math fonts')
args=parser.parse_args()
if not (3,10)<=sys.version_info[:2]<(3,15):raise SystemExit('Python 3.10–3.14 is required.')
env=root/'.venv'
venv.EnvBuilder(with_pip=True).create(env)
python=env/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
subprocess.run([str(python),'-m','pip','install','--requirement',str(root/'requirements.lock')],check=True)
print('Runtime:',python,flush=True)
subprocess.run([str(python),str(root/'scripts/doctor.py')]+(['--formulas'] if args.formulas else []),check=True)
