#!/usr/bin/env python3
"""Replace manifest raster atoms with lossless native filled Bezier paint parts.
The input geometry comes from Illustrator's expanded trace, not an SVG picture.
"""
import argparse,copy,json,math
from pathlib import Path

def convert(asset,geometry):
 x,y,w,h=asset['bounds'];sx=w/geometry['width'];sy=h/geometry['height'];result=[]
 def point(p):return [x+p[0]*sx,y+(geometry['height']-p[1])*sy]
 for idx,atom in enumerate(geometry['atoms']):
  if len(atom['parts'])>1 and atom.get('fill_rule')!='nonzero':raise ValueError('Even-odd compound fill requires winding normalization before PowerPoint export')
  cmds=[]
  for part in atom['parts']:
   ps=part['points']
   if len(ps)<2:continue
   cmds.append(['M']+point(ps[0][0]))
   count=len(ps) if part['closed'] else len(ps)-1
   for j in range(count):
    a=ps[j];b=ps[(j+1)%len(ps)]
    if a[2]==a[0] and b[1]==b[0]:cmds.append(['L']+point(b[0]))
    else:cmds.append(['C']+point(a[2])+point(b[1])+point(b[0]))
   if part['closed']:cmds.append(['Z'])
  if not cmds:continue
  points=[(c[j],c[j+1]) for c in cmds for j in range(1,len(c),2)]
  X=min(p[0] for p in points);Y=min(p[1] for p in points);W=max(p[0] for p in points)-X;H=max(p[1] for p in points)-Y
  fill=''.join(f'{max(0,min(255,round(v))):02X}' for v in atom['fill'])
  # Native picture extraction can declare only audited connector-fragment removal regions.
  drop=False
  for r in asset.get('remove_neutral_fragments',[]):
   if max(atom['fill'])<r['max_gray'] and max(atom['fill'])-min(atom['fill'])<35 and X>=r['bounds'][0] and Y>=r['bounds'][1] and X+W<=r['bounds'][2] and Y+H<=r['bounds'][3]:drop=True
  if drop:continue
  result.append(dict(id=asset['id']+f'.path-{idx:05}',type='path',bounds=[X,Y,max(W,.001),max(H,.001)],commands=cmds,fill=fill))
 return result

def replace(data,root,vector_dir,batch_size):
 result=copy.deepcopy(data);objects=[];report=[]
 for obj in data['objects']:
  if obj['type']!='image':objects.append(obj);continue
  file=vector_dir/(obj['id']+'.json')
  if not file.exists():raise FileNotFoundError('Unresolved complex vector asset: '+str(file))
  g=json.loads(file.read_text());paths=convert(obj,g)
  if not paths:raise ValueError('Empty complex asset '+obj['id'])
  for k in range(0,len(paths),batch_size):
   chunk=paths[k:k+batch_size];x=min(p['bounds'][0] for p in chunk);y=min(p['bounds'][1] for p in chunk);X=max(p['bounds'][0]+p['bounds'][2] for p in chunk);Y=max(p['bounds'][1]+p['bounds'][3] for p in chunk)
   objects.append(dict(id=obj['id']+f'.batch-{k//batch_size:04}',type='group',bounds=[x,y,X-x,Y-y],children=chunk))
  report.append(dict(id=obj['id'],source_atoms=len(g['atoms']),native_paths=len(paths),removed_fragments=len(g['atoms'])-len(paths),illustrator=g['illustrator']))
 result.update(mode='native',objects=objects,vector_provenance=report)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--vectors',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--paths-per-batch',type=int,default=8);a=ap.parse_args()
 if not 1<=a.paths_per_batch<=50:raise ValueError('paths-per-batch must be 1..50')
 if a.output.exists():raise FileExistsError(a.output)
 r=replace(json.loads(a.manifest.read_text()),a.manifest.parent,a.vectors,a.paths_per_batch);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r['vector_provenance']))
