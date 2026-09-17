#!/usr/bin/env python3
"""Inspect dependencies, math tools and requested fonts without changing applications."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys


def diagnose(manifest=None, formulas=False):
    checks={'python':{'version':platform.python_version(),'ok':(3,10)<=sys.version_info[:2]<(3,15)},'platform':{'name':platform.system(),'ok':platform.system() in ('Darwin','Windows')}}
    for name,version in {'Pillow':'12.1.0','fonttools':'4.61.1'}.items():
        try:actual=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:actual=None
        checks[name]={'version':actual,'expected':version,'ok':actual==version}
    data=json.loads(Path(manifest).read_text(encoding='utf-8')) if manifest else {}
    if formulas or data.get('formulas'):
        for tool in ('xelatex','dvisvgm','kpsewhich'):
            path=shutil.which(tool);checks[tool]={'path':path,'ok':bool(path)}
        if checks['kpsewhich']['ok']:
            for name in ('unicode-math.sty','standalone.cls','XITSMath-Bold.otf','XITS-Bold.otf'):
                result=subprocess.run(['kpsewhich',name],capture_output=True,text=True,timeout=10)
                checks[name]={'path':result.stdout.strip(),'ok':result.returncode==0 and bool(result.stdout.strip())}
    if data.get('labels'):
        try:
            from font_probe import inspect_fonts
            checks['fonts']={'ok':True,'resolved':inspect_fonts(data['labels'])}
        except (ValueError,OSError,ImportError) as error:checks['fonts']={'ok':False,'error':str(error)}
    if platform.system()=='Darwin':
        proc=subprocess.run(['osascript','-e','application id "com.adobe.illustrator" is running'],capture_output=True,text=True,timeout=15)
        checks['illustrator']={'ok':proc.returncode==0 and proc.stdout.strip()=='true','running':proc.stdout.strip()=='true'}
    elif platform.system()=='Windows':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,r'Illustrator.Application\CLSID') as key:progid=winreg.QueryValue(key,None)
            checks['illustrator']={'ok':True,'registered_clsid':progid,'desktop_validation':'required'}
        except OSError:checks['illustrator']={'ok':False,'error':'Illustrator COM registration missing'}
    return {'ok':all(c['ok'] for c in checks.values()),'checks':checks,'note':'Dependency checks do not prove desktop drawing or visual fidelity.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--formulas',action='store_true')
    args=parser.parse_args();result=diagnose(args.manifest,args.formulas)
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['ok'] else 1)
