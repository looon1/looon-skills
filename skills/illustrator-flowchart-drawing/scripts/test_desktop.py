#!/usr/bin/env python3
"""Run native Illustrator acceptance in newly created, owned test documents on Mac or Windows."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from PIL import Image, ImageDraw, ImageFont
from prepare_job import prepare
from verify_delivery import verify, compare_images


def run_test(root):
    if root.exists():raise ValueError('Use a new test directory')
    root.mkdir(parents=True)
    scripts=Path(__file__).parent
    manifest=scripts.parent/'tests/smoke-manifest.json'
    source=root/'reference.png';Image.new('RGB',(900,620),'white').save(source)
    job,output=root/'job',root/'output'
    prepare(source,job,output,manifest)

    def command(stage,*options):
        if sys.platform=='darwin':return [sys.executable,str(scripts/'run-illustrator-mac.py'),'--job-dir',str(job),'--stage',stage,*options]
        aliases={'--start':'-Start','--max-batches':'-MaxBatches'}
        return ['powershell','-NoProfile','-File',str(scripts/'run-illustrator.ps1'),'-JobDir',str(job),'-Stage',stage,*[aliases.get(v,v) for v in options]]

    def stage(name,*options):
        print('STAGE',name,*options,flush=True)
        subprocess.run(command(name,*options),check=True,timeout=300)

    def execute(path,check=True):
        if sys.platform=='darwin':
            result=subprocess.run(['osascript','-e','on run argv\nset scriptFile to POSIX file (item 1 of argv)\ntell application id "com.adobe.illustrator" to do javascript scriptFile\nend run',str(path)],capture_output=True,text=True,timeout=120)
        else:
            bridge=root/'bridge.ps1'
            bridge.write_text('param([string]$ScriptPath)\n$ErrorActionPreference="Stop"\n$app=New-Object -ComObject Illustrator.Application\ntry{$app.DoJavaScriptFile($ScriptPath)}finally{[void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)}\n')
            result=subprocess.run(['powershell','-NoProfile','-File',str(bridge),'-ScriptPath',str(path)],capture_output=True,text=True,timeout=120)
        if check and result.returncode:raise RuntimeError(result.stderr or result.stdout)
        return result

    stage('compose')
    addition=root/'add-art.jsx'
    addition.write_text((scripts.parent/'tests/add-complex-fixture.jsx').read_text().replace('__TARGET__',json.dumps((output/'figure.ai').as_posix())),encoding='ascii')
    execute(addition);stage('export')
    baseline=root/'source.png';baseline.write_bytes((output/'preview.png').read_bytes())
    stage('live','--start','--max-batches','1')
    assert (job/'live-cursor.txt').read_text().strip()=='1'
    # The first static transaction must contain no complex illustration group.
    batches=job/'live-batches';ops=json.loads((batches/'0.json').read_text())
    assert not any(o.get('name')=='Complex fixture' for o in ops)
    assert sum(o.get('kind')=='TextFrame' for o in ops)==4
    execute(batches/'1.jsx')
    cursor=(job/'live-cursor.txt').read_text()
    (job/'interrupt-after-object.txt').write_text('one-shot test fault')
    failed=execute(batches/'2.jsx',check=False)
    assert failed.returncode!=0 and 'TEST_INTERRUPTION_AFTER_OBJECT' in failed.stderr+failed.stdout
    assert (job/'live-cursor.txt').read_text()==cursor
    stage('live','--start','--max-batches','1')
    assert (job/'live-cursor.txt').read_text().strip()=='3'
    # Leave the runner active and issue a real Step command, then verify a stable pause.
    progress=root/'step-runner.log'
    with progress.open('w') as stream:
        runner=subprocess.Popen(command('live'),stdout=stream,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+30
            while 'Ready.' not in progress.read_text() and 'Ready.' not in (job/'live.log').read_text():
                if runner.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Live controller not ready: '+progress.read_text())
                time.sleep(.1)
            (job/'live-command.txt').write_text('step')
            deadline=time.monotonic()+30
            while (job/'live-cursor.txt').read_text().strip()!='4':
                if runner.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Step failed: '+progress.read_text())
                time.sleep(.1)
            time.sleep(1)
            assert (job/'live-cursor.txt').read_text().strip()=='4'
            assert (job/'live-command.txt').read_text().strip()=='pause'
            (job/'live-command.txt').write_text('stop')
            runner.wait(timeout=10)
            assert runner.returncode==0,progress.read_text()
        finally:
            if runner.poll() is None:runner.terminate()
    assert (job/'live-cursor.txt').read_text().strip()=='4'
    session=json.loads((job/'live-session.json').read_text())
    closing=root/'close-owned-checkpoint.jsx'
    closing.write_text('var d=app.activeDocument;d.layers.getByName('+json.dumps(session['token'])+');if(d.fullName.fsName!==new File('+json.dumps((job/'live-checkpoint.ai').as_posix())+').fsName)throw new Error("Not the owned checkpoint");d.close(SaveOptions.DONOTSAVECHANGES);',encoding='ascii')
    execute(closing)
    stage('live','--start')
    stage('verify')
    report=verify(output,job,reopened=output/'preview-reopened.png')
    report['prepared_to_live']=compare_images(baseline,output/'preview.png',output/'prepared-live')
    report['svg_round_trip']=compare_images(output/'preview.png',output/'preview-svg-reopened.png',output/'svg-round-trip')
    report.update(platform=sys.platform,partial_batch_recovery=True,disk_checkpoint_recovery=True,single_step=True,pause_seconds=1,desktop_tested=True)
    if report['save_reopen_comparison']['different_pixels']!=0:raise ValueError('AI save/reopen pixels changed')
    # Small native rotation quantization is recorded, not called reference equality.
    if report['prepared_to_live']['different_pixels']>500:raise ValueError('Unexpected playback appearance drift')
    # Completed sessions must reopen the final AI rather than the partial checkpoint.
    closing.write_text('var d=app.activeDocument;if(d.fullName.fsName!==new File('+json.dumps((output/'figure-live.ai').as_posix())+').fsName)throw new Error("Not the owned final");d.close(SaveOptions.DONOTSAVECHANGES);',encoding='ascii')
    execute(closing);stage('live','--start');stage('verify')
    report['completed_session_recovery']=True

    # Formula-only documents require no placeholder text and respect explicit paint order.
    case=root/'formula-only';case.mkdir();job=case/'job';output=case/'output'
    source=case/'reference.png';Image.new('RGB',(400,220),'white').save(source)
    formula={'id':'F001','tex':r'\frac{\hat{x}_i^2+\alpha}{\beta}', 'bounds':[30,40,300,150],'font_size':36}
    background={'name':'Background','type':'rect','bounds':[0,0,400,220],'fill':[255,255,255],'background':True}
    overlay={'name':'Overlay','type':'rect','bounds':[80,40,100,100],'fill':[245,205,205]}
    data={'labels':[],'formulas':[formula],'nativeLayout':{'elements':[background,overlay]},'paint_order':['Background','Formula F001','Overlay']}
    manifest=case/'manifest.json';manifest.write_text(json.dumps(data))
    prepare(source,job,output,manifest);stage('compose')
    baseline=case/'source.png';baseline.write_bytes((output/'preview.png').read_bytes())
    stage('live','--start');stage('verify');check=verify(output,job,reopened=output/'preview-reopened.png')
    assert check['native_text_frames']==0 and check['typeset_formulas']==1
    assert compare_images(baseline,output/'preview.png',output/'paint-order')['different_pixels']==0
    report['formula_only_and_paint_order']=True

    # Migrate only a copied old Skill document, including legacy nonuniform text scales.
    case=root/'legacy';case.mkdir();job=case/'job';output=case/'output'
    source=case/'reference.png';Image.new('RGB',(400,220),'white').save(source)
    original=case/'legacy.ai';fixture=case/'fixture.jsx'
    fixture.write_text((scripts.parent/'tests/legacy-fixture.jsx').read_text().replace('__TARGET__',json.dumps(original.as_posix())),encoding='ascii');execute(fixture)
    before=original.read_bytes()
    data={'labels':[{'id':'new-label','text':'Legacy label','font':'Arial-BoldMT','font_size':18,'baseline':[25,40],'bounds':[20,20,200,60],'repair':'none'}],
          'groups':[{'name':'Retained','bounds':[10,10,350,210]}],
          'nativeLayout':{'elements':[background]},'paint_order':['Background','Retained','Legacy repair','new-label']}
    manifest=case/'manifest.json';manifest.write_text(json.dumps(data))
    prepare(source,job,output,manifest,original);stage('structure');stage('verify')
    assert original.read_bytes()==before
    stage('live','--start');stage('verify');check=verify(output,job,reopened=output/'preview-reopened.png')
    assert check['native_text_frames']==1 and check['save_reopen_comparison']['different_pixels']==0
    report['legacy_text_migration_and_locked_paint_order']=True
    # Exercise the actual Image Trace -> text repair -> native rebuild route as well.
    from font_probe import inspect_fonts
    case=root/'trace';case.mkdir();job=case/'job';output=case/'output';source=case/'reference.png'
    image=Image.new('RGB',(320,180),'white');drawing=ImageDraw.Draw(image)
    drawing.ellipse((170,35,270,135),fill=(219,166,204),outline=(90,45,100),width=3)
    drawing.ellipse((197,60,238,100),fill=(158,94,169))
    font=inspect_fonts([{'text':'A','font':'Arial-BoldMT'}])[0]['file']
    drawing.text((40,50),'A',font=ImageFont.truetype(font,32),fill=(20,20,20));image.save(source)
    data={'labels':[{'id':'label-A','text':'A','font':'Arial-BoldMT','font_size':32,'baseline':[40,80],'bounds':[35,45,80,100],'repair':'glyphs','background':[255,255,255]}],
          'groups':[{'name':'Cell','bounds':[165,30,276,141]}],
          'nativeLayout':{'elements':[{'name':'Background','type':'rect','bounds':[0,0,320,180],'fill':[255,255,255],'background':True},{'name':'Frame','type':'rect','bounds':[10,10,310,170],'stroke':[180,55,45],'width':3}]}}
    manifest=case/'manifest.json';manifest.write_text(json.dumps(data));prepare(source,job,output,manifest)
    stage('trace');stage('rebuild');stage('live','--start');stage('verify')
    check=verify(output,job,reopened=output/'preview-reopened.png')
    assert check['native_text_frames']==1 and check['save_reopen_comparison']['different_pixels']==0
    report['trace_rebuild_text_repair']=True
    (root/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    if sys.platform not in ('darwin','win32'):raise SystemExit('Desktop Illustrator on macOS or Windows is required.')
    run_test(args.output_dir.resolve())
