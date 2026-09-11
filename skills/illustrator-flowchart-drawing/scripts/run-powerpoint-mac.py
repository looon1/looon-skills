#!/usr/bin/env python3
"""Live native PowerPoint cache playback via the installed macOS object model.
Each copy/paste creates real objects on the target slide; no slideshow or reveal animation.
"""
import argparse, hashlib, json, platform, subprocess, time, zipfile
from pathlib import Path
from xml.etree import ElementTree as E

def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')+'"'
def apple(body,timeout=55):
 code='with timeout of 50 seconds\ntell application "Microsoft PowerPoint"\n'+body+'\nend tell\nend timeout'
 r=subprocess.run(['osascript','-e',code],capture_output=True,text=True,timeout=timeout)
 if r.returncode:raise RuntimeError(r.stderr.strip())
 return r.stdout.strip()
def audit(path):
 ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
 with zipfile.ZipFile(path) as z:
  slides=[n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
  if len(slides)!=1:raise ValueError('Expected one cache slide')
  r=E.fromstring(z.read(slides[0]));tree=r.find('p:cSld/p:spTree',ns);objs=list(tree)[2:]
  return [{'name':o.find('.//p:cNvPr',ns).get('name'),'kind':o.tag.split('}')[-1], 'text':'\n'.join(t.text or '' for t in o.findall('.//a:t',ns)), 'appearance':hashlib.sha256(json.dumps([[(el.tag.split('}')[-1],sorted(el.attrib.items())) for el in paint.iter()] for sp in o.findall('.//p:spPr',ns) for paint in sp if paint.tag.split('}')[-1] in {'solidFill','gradFill','noFill','ln'}],sort_keys=True).encode()).hexdigest(), 'native_paths':len(o.findall('.//a:custGeom',ns)), 'picture_descendants':len(o.findall('.//p:pic',ns)), 'curve_geometry':hashlib.sha256(json.dumps([[(el.tag.split('}')[-1],sorted(el.attrib.items())) for el in pa.iter()] for pa in o.findall('.//a:pathLst/a:path',ns)],sort_keys=True).encode()).hexdigest()} for o in objs]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--job-dir',type=Path,required=True);ap.add_argument('--stage',choices=['start','step','run','finish','inspect'],required=True);ap.add_argument('--output',type=Path);ap.add_argument('--delay',type=float,default=0);ap.add_argument('--batch-size',type=int,default=12);ap.add_argument('--until',type=int,help='Stop after this many top-level objects for regional review');args=ap.parse_args()
 if platform.system()!='Darwin':raise SystemExit('This adapter requires macOS; use the Windows COM route on Windows.')
 if not 0<=args.delay<=5 or not 1<=args.batch_size<=30:raise ValueError('Use delay 0..5 and batch size 1..30')
 cache=args.cache.resolve();job=args.job_dir.resolve();statefile=job/'powerpoint-state.json';report=json.loads(cache.with_suffix('.json').read_text());digest=hashlib.sha256(cache.read_bytes()).hexdigest()
 if report['cache_sha256']!=digest:raise ValueError('Cache hash mismatch; revalidate the cache')
 expected=audit(cache)
 if [o['name'] for o in expected]!=[o['id'] for o in report['objects']]:raise ValueError('Cache inventory differs from manifest report')
 job.mkdir(parents=True,exist_ok=True)
 def save_state(state):
  temp=statefile.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2));temp.replace(statefile)
 if args.stage=='start':
  if statefile.exists():raise ValueError('Existing session: inspect/resume instead of starting again')
  # Open a session copy; never change the validated cache or the user's open deck.
  session=job/'powerpoint-session.pptx'
  if session.exists():raise FileExistsError(session)
  session.write_bytes(cache.read_bytes())
  if apple('return running')!='true':raise RuntimeError('Open PowerPoint first')
  apple(f'open POSIX file {quote(session)}\nset p to active presentation\nset s to make new slide at end of p with properties {{layout:slide layout blank}}\ngo to slide view of active window number 2\nreturn count shapes of s')
  state={'cache_sha256':digest,'session':str(session),'status':'READY','completed':0}
  save_state(state);print(json.dumps(state));return
 state=json.loads(statefile.read_text())
 if state['cache_sha256']!=digest:raise ValueError('Session/cache mismatch')
 if state['status']=='DONE':print(json.dumps(state));return
 session=state['session'];bind=f'set p to active presentation\nif (full name of p as text) is not {quote(session)} then error "Target changed; activate the task session and resume."\nset s to slide 2 of p\nset targetWindow to document window 1 of p\n'
 def inventory():
  text=apple(bind+"if (count shapes of s) is 0 then return \"\"\nset shapeNames to name of every shape of s\nset AppleScript's text item delimiters to linefeed\nreturn shapeNames as text")
  return text.splitlines() if text else []
 existing=inventory();names=[o['name'] for o in expected]
 if existing!=names[:len(existing)]:raise ValueError('Target order/names differ from expected prefix; inspect before continuing')
 state['completed']=len(existing);save_state(state)
 if args.stage=='inspect':print(json.dumps(state));return
 if args.stage in ['step','run']:
  limit=min(len(names),len(existing)+1) if args.stage=='step' else min(len(names),args.until if args.until is not None else len(names))
  if limit<len(existing):raise ValueError('--until is behind current progress')
  for begin in range(len(existing),limit,args.batch_size):
   if (job/'pause').exists():state['status']='PAUSED';save_state(state);print(json.dumps(state));return
   end=min(begin+args.batch_size,limit);lines=[bind,'set previousClipboard to the clipboard as record','try']
   for i in range(begin,end):
    lines.extend([f'set src to shape {i+1} of slide 1 of p','copy shape src','go to slide view of targetWindow number 2','paste object view of targetWindow',f'set dst to last shape of s',f'set name of dst to {quote(names[i])}','set left position of dst to left position of src','set top of dst to top of src','set width of dst to width of src','set height of dst to height of src',f'delay {args.delay}'])
   lines+=['on error messageText number errorNumber','set the clipboard to previousClipboard','error messageText number errorNumber','end try','set the clipboard to previousClipboard','return count shapes of s']
   count=int(apple('\n'.join(lines)))
   if count!=end:raise ValueError('Native shape readback count mismatch')
   state.update(completed=count,status='DRAWING');save_state(state);print(json.dumps({'completed':count,'total':len(names)}),flush=True)
  state['status']='DRAWN' if limit==len(names) else 'PAUSED';save_state(state);return
 if args.stage=='finish':
  if len(existing)!=len(names):raise ValueError('Drawing incomplete')
  if args.output is None:raise ValueError('--output is required')
  output=args.output.resolve()
  if output.exists():raise FileExistsError(output)
  output.parent.mkdir(parents=True,exist_ok=True)
  # Only remove the source slide of this task-created session.
  apple(bind+f'delete slide 1 of p\nsave p in POSIX file {quote(output)} as save as Open XML presentation',timeout=55)
  actual=audit(output)
  if actual!=expected:raise ValueError('Saved native inventory/text differs from cache; inspect the output')
  state.update(status='DONE',output=str(output),verified_objects=len(actual),native=report['counts']['native'],pictures=report['counts']['picture'],groups=report['counts'].get('groups',0));save_state(state);print(json.dumps(state,ensure_ascii=False))
if __name__=='__main__':main()
