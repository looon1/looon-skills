#!/usr/bin/env python3
"""Compile explicit native geometry into a PowerPoint playback cache (stdlib only)."""
import argparse, hashlib, json, math, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as E
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PK='http://schemas.openxmlformats.org/package/2006/relationships'
NS={'p':P,'a':A}
for p,u in [('p',P),('a',A),('r',R)]: E.register_namespace(p,u)
def node(parent, tag, attrs=None, text=None):
 e=E.SubElement(parent,'{'+({'p':P,'a':A}[tag.split(':')[0]])+'}'+tag.split(':')[1],{k:str(v) for k,v in (attrs or {}).items()});e.text=text;return e
def color(parent,c):
 if not re.fullmatch('[0-9A-Fa-f]{6}',c):raise ValueError('Expected hex RGB: '+str(c))
 return node(parent,'a:srgbClr',{'val':c.upper()})
def fill(parent,c):
 if c is None:node(parent,'a:noFill')
 elif isinstance(c,list):
  g=node(parent,'a:gradFill',{'rotWithShape':'1'}); gs=node(g,'a:gsLst')
  for i,v in enumerate(c):color(node(gs,'a:gs',{'pos':round(i*100000/(len(c)-1))}),v)
  node(g,'a:lin',{'ang':'5400000','scaled':'1'})
 else:color(node(parent,'a:solidFill'),c)
def compile_manifest(data,manifest_dir):
 w,h=data['width'],data['height']; scale=9144000/w
 if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in (w,h)):raise ValueError('Invalid canvas')
 st=E.Element('{'+P+'}spTree');node(node(st,'p:nvGrpSpPr'),'p:cNvPr',{'id':1,'name':''});nv=st[0];node(nv,'p:cNvGrpSpPr');node(nv,'p:nvPr');node(st,'p:grpSpPr')
 media={}; rels=[]; ids=set(); stats={'text':0,'native':0,'picture':0,'groups':0}
 for i,o in enumerate(data['objects'],2):
  name=o['id'];kind=o['type']
  if not name or name in ids:raise ValueError('Duplicate/empty object id: '+name)
  ids.add(name)
  if kind not in ['rect','ellipse','path','text','image','group']:raise ValueError('Unsupported type: '+kind)
  x,y,bw,bh=o['bounds']
  if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (x,y,bw,bh)) or bw<=0 or bh<=0:raise ValueError('Invalid bounds: '+name)
  if x<0 or y<0 or x+bw>w+.1 or y+bh>h+.1:raise ValueError('Outside canvas: '+name)
  if kind=='group':
   if not o.get('children'):raise ValueError('Empty native group')
   children,cm,cr,cs,_=compile_manifest(dict(width=w,height=h,mode='native',objects=o['children']),manifest_dir)
   g=node(st,'p:grpSp');nv=node(g,'p:nvGrpSpPr');node(nv,'p:cNvPr',{'id':i,'name':name});node(nv,'p:cNvGrpSpPr');node(nv,'p:nvPr')
   gp=node(g,'p:grpSpPr');tr=node(gp,'a:xfrm')
   for tag,attrs in [('off',{'x':round(x*scale),'y':round(y*scale)}),('ext',{'cx':round(bw*scale),'cy':round(bh*scale)}),('chOff',{'x':round(x*scale),'y':round(y*scale)}),('chExt',{'cx':round(bw*scale),'cy':round(bh*scale)})]:node(tr,'a:'+tag,attrs)
   for ch in list(children)[2:]:g.append(ch)
   for key in stats:stats[key]+=cs[key]
   stats['groups']+=1
   continue
  pic=kind=='image'; s=node(st,'p:pic' if pic else 'p:sp'); nv=node(s,'p:nvPicPr' if pic else 'p:nvSpPr');node(nv,'p:cNvPr',{'id':i,'name':name});node(nv,'p:cNvPicPr' if pic else 'p:cNvSpPr',{'txBox':'1'} if kind=='text' else {});node(nv,'p:nvPr')
  if pic:
   if data.get('mode','native')!='hybrid':raise ValueError('Images require explicit hybrid mode')
   if not o.get('raster_reason') or not o.get('atomic_raster_unit') or o.get('contains_text',True):raise ValueError('Image requires atomic raster declaration without text: '+name)
   src=(manifest_dir/o['file']).resolve()
   if src.suffix.lower()!='.png':raise ValueError('Only PNG cache assets supported')
   rid='rIdAsset'+str(i); filename='asset'+str(i)+'.png';media[filename]=src.read_bytes();rels.append((rid,'../media/'+filename))
   bf=node(s,'p:blipFill');node(bf,'a:blip',{'{'+R+'}embed':rid});node(node(bf,'a:stretch'),'a:fillRect')
  sp=node(s,'p:spPr');tr=node(sp,'a:xfrm');node(tr,'a:off',{'x':round(x*scale),'y':round(y*scale)});node(tr,'a:ext',{'cx':round(bw*scale),'cy':round(bh*scale)})
  if kind=='path':
   cg=node(sp,'a:custGeom');node(cg,'a:avLst');node(cg,'a:gdLst');node(cg,'a:ahLst');node(cg,'a:cxnLst');node(cg,'a:rect',{'l':'l','t':'t','r':'r','b':'b'});pl=node(cg,'a:pathLst');pa=node(pl,'a:path',{'w':round(bw*1000),'h':round(bh*1000)})
   for cmd in o['commands']:
    op=cmd[0]; nums=cmd[1:]
    arity={'M':2,'L':2,'C':6,'Q':4,'Z':0}
    if op not in arity or len(nums)!=arity[op] or not all(math.isfinite(v) for v in nums):raise ValueError('Invalid path command')
    q=node(pa,'a:'+{'M':'moveTo','L':'lnTo','C':'cubicBezTo','Q':'quadBezTo','Z':'close'}[op])
    for j in range(0,len(nums),2):node(q,'a:pt',{'x':round((nums[j]-x)*1000),'y':round((nums[j+1]-y)*1000)})
  else:node(node(sp,'a:prstGeom',{'prst':'ellipse' if kind=='ellipse' else 'rect'}),'a:avLst')
  if not pic:fill(sp,o.get('fill'))
  ln=node(sp,'a:ln',{'w':round(o.get('stroke_width',1)*scale)})
  fill(ln,o.get('stroke'))
  if o.get('dash'):node(ln,'a:prstDash',{'val':'dash'})
  if o.get('arrow'):node(ln,'a:tailEnd',{'type':'triangle','w':'sm','len':'sm'})
  if kind=='text':
   tx=node(s,'p:txBody');node(tx,'a:bodyPr',{'wrap':'none','lIns':'0','tIns':'0','rIns':'0','bIns':'0','anchor':'t'});node(tx,'a:lstStyle')
   for line in o['text'].split('\n'):
    pp=node(tx,'a:p');node(pp,'a:pPr',{'algn':o.get('align','l')});rr=node(pp,'a:r');pr=node(rr,'a:rPr',{'lang':'en-US','sz':round(o.get('font_size',28)*scale/127), 'b':'1' if o.get('bold') else '0'});fill(pr,o.get('color','111111'));node(pr,'a:latin',{'typeface':o.get('font','Arial')});node(rr,'a:t',text=line)
   stats['text']+=1
  stats['picture' if pic else 'native']+=1
 return st,media,rels,stats,scale

def prepare(manifest,output):
 data=json.loads(manifest.read_text());st,media,rels,stats,scale=compile_manifest(data,manifest.parent)
 all_names=set()
 for i,e in enumerate(st.findall('.//p:cNvPr',NS),1):
  e.set('id',str(i));name=e.get('name')
  if name and name in all_names:raise ValueError('Duplicate nested object name: '+name)
  all_names.add(name)
 template=Path(__file__).resolve().parents[1]/'assets/powerpoint-blank.pptx'
 if output.exists():raise FileExistsError(output)
 output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(template) as z,zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as out:
  for name in z.namelist():
   b=z.read(name)
   if name=='ppt/slides/slide1.xml':
    r=E.fromstring(b);cs=r.find('p:cSld',NS);old=cs.find('p:spTree',NS);cs.remove(old);cs.insert(0,st);b=E.tostring(r,encoding='utf-8',xml_declaration=True)
   elif name=='ppt/presentation.xml':
    r=E.fromstring(b);sz=r.find('p:sldSz',NS);sz.set('cx',str(round(data['width']*scale)));sz.set('cy',str(round(data['height']*scale)));sz.set('type','custom');b=E.tostring(r,encoding='utf-8',xml_declaration=True)
   elif name=='ppt/slides/_rels/slide1.xml.rels':
    r=E.fromstring(b)
    for rid,target in rels:E.SubElement(r,'{'+PK+'}Relationship',{'Id':rid,'Type':R+'/image','Target':target})
    b=E.tostring(r,encoding='utf-8',xml_declaration=True)
   elif name=='[Content_Types].xml':
    r=E.fromstring(b);ct='http://schemas.openxmlformats.org/package/2006/content-types'
    if not any(c.get('Extension')=='png' for c in r):E.SubElement(r,'{'+ct+'}Default',{'Extension':'png','ContentType':'image/png'})
    b=E.tostring(r,encoding='utf-8',xml_declaration=True)
   out.writestr(name,b)
  for name,b in media.items():out.writestr('ppt/media/'+name,b)
 report={'schema':1,'cache_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'mode':data.get('mode','native'),'counts':stats,'objects':[{'id':o['id'],'type':o['type']} for o in data['objects']]}
 output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--output',required=True,type=Path);args=ap.parse_args();print(json.dumps(prepare(args.manifest.resolve(),args.output.resolve()),ensure_ascii=False))
