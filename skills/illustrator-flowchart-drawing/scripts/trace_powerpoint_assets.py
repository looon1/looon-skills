#!/usr/bin/env python3
"""Trace individually inventoried complex assets with installed Illustrator; export real paths.
Pillow is required only to decode RGBA and produce white-matted TIFF inputs.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from PIL import Image
TEMPLATE=r'''#target illustrator
(function(){
var cfg=__CONFIG__, log=new File(cfg.job+'/trace.log');log.encoding='UTF-8';log.open('w');log.close();
function record(s){log.open('a');log.writeln(s);log.close();}
function encode(x){if(x===null)return 'null';if(typeof x==='number'||typeof x==='boolean')return String(x);if(typeof x==='string')return '"'+x.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\n/g,'\\n')+'"';if(x instanceof Array){var a=[];for(var i=0;i<x.length;i++)a.push(encode(x[i]));return '['+a.join(',')+']';}var a=[];for(var k in x)if(x.hasOwnProperty(k))a.push(encode(k)+':'+encode(x[k]));return '{'+a.join(',')+'}';}
function rgb(c){if(c.typename==='RGBColor')return [c.red,c.green,c.blue];if(c.typename==='GrayColor')return [255*(1-c.gray/100),255*(1-c.gray/100),255*(1-c.gray/100)];if(c.typename==='CMYKColor')return app.convertSampleColor(ImageColorSpace.CMYK,[c.cyan,c.magenta,c.yellow,c.black],ImageColorSpace.RGB,ColorConvertPurpose.defaultpurpose);throw new Error('Unsupported fill '+c.typename);}
function subpath(p){var a=[],pts=p.pathPoints;for(var i=0;i<pts.length;i++)a.push([pts[i].anchor,pts[i].leftDirection,pts[i].rightDirection]);return {closed:p.closed,points:a};}
function collect(item,out){
 if(item.typename==='GroupItem'||item.typename==='Layer'){
  if(item.typename==='GroupItem'&&item.clipped)throw new Error('Clipped group requires an explicit clipping adapter');
  // Illustrator direct pageItems are front-to-back; PowerPoint insertion is back-to-front.
  var items=[];for(var i=0;i<item.pageItems.length;i++)if(item.pageItems[i].parent===item)items.push(item.pageItems[i]);
  for(i=items.length-1;i>=0;i--)collect(items[i],out);return;
 }
 if(item.typename==='CompoundPathItem'){
  if(!item.pathItems.length)return;var parts=[];for(var j=0;j<item.pathItems.length;j++)parts.push(subpath(item.pathItems[j]));var p=item.pathItems[0];
 }else if(item.typename==='PathItem'){if(item.guides)return;var p=item,parts=[subpath(item)];}
 else throw new Error('Unexpected traced object '+item.typename);
 if(p.clipping||p.stroked||!p.filled||item.opacity!==100)throw new Error('Expected opaque filled tracing paths');
 out.push({fill:rgb(p.fillColor),fill_rule:p.evenodd?"evenodd":"nonzero",bounds:item.geometricBounds,parts:parts});
}
var previous=app.userInteractionLevel;
try{
 app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS;
 var presets=app.tracingPresetsList,preset=null;for(var i=0;i<presets.length;i++)if(presets[i]==='High Fidelity Photo'||presets[i]==='\u9ad8\u4fdd\u771f\u5ea6\u7167\u7247')preset=presets[i];if(!preset)throw new Error('Inspect localized high fidelity preset first');
 for(var k=0;k<cfg.assets.length;k++){
  var a=cfg.assets[k],done=new File(a.output);if(done.exists){record('REUSE '+a.id);continue;}
  var d=app.open(new File(a.input));if(d.rasterItems.length!==1)throw new Error('Expected one RasterItem');
  d.artboards[0].artboardRect=[0,a.height,a.width,0];var r=d.rasterItems[0];r.width=a.width;r.height=a.height;r.position=[0,a.height];
  var t=r.trace(),opt=t.tracing.tracingOptions;if(!opt.loadFromPreset(preset))throw new Error('Preset load failed');opt.pathFidelity=90;opt.cornerFidelity=80;opt.noiseFidelity=1;opt.ignoreWhite=true;
  app.redraw();record('TRACE '+a.id+' paths='+t.tracing.pathCount);t.tracing.expandTracing();app.redraw();
  if(d.rasterItems.length||d.placedItems.length)throw new Error('Trace not expanded');
  var atoms=[];for(var l=d.layers.length-1;l>=0;l--)collect(d.layers[l],atoms);
  done.encoding='UTF-8';done.open('w');done.write(encode({id:a.id,width:a.width,height:a.height,illustrator:app.version,preset:preset,atoms:atoms}));done.close();
  var opts=new IllustratorSaveOptions();opts.pdfCompatible=true;d.saveAs(new File(a.ai),opts);
  record('DONE '+a.id+' atoms='+atoms.length);
 }
 record('DONE');
}catch(e){record('ERROR '+String(e));throw e;}finally{app.userInteractionLevel=previous;}
})();'''
def main():
 ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--job-dir',type=Path,required=True);ap.add_argument('--only',help='Optional exact semantic asset id');ap.add_argument('--execute',action='store_true');args=ap.parse_args();m=args.manifest.resolve();job=args.job_dir.resolve();job.mkdir(parents=True,exist_ok=True)
 data=json.loads(m.read_text());assets=[];hashfile=job/'input-hashes.json';known=json.loads(hashfile.read_text()) if hashfile.exists() else {}
 for o in data['objects']:
  if o['type']!='image' or (args.only and args.only!=o['id']):continue
  stem=o['id'];sourcehash=hashlib.sha256((m.parent/o['file']).read_bytes()).hexdigest()
  if (job/(stem+'.json')).exists() and known.get(stem)!=sourcehash:raise ValueError('Unverified or changed cached asset; use a fresh vector job directory: '+stem)
  known[stem]=sourcehash
  img=Image.open(m.parent/o['file']).convert('RGBA');white=Image.new('RGBA',img.size,'white');white.alpha_composite(img);source=job/(stem+'.tif');white.convert('RGB').save(source)
  assets.append({'id':stem,'input':str(source),'output':str(job/(stem+'.json')),'ai':str(job/(stem+'.ai')),'width':img.width,'height':img.height})
 if not assets:raise ValueError('No matching inventoried assets')
 hashfile.write_text(json.dumps(known,indent=2))
 script=job/'trace-assets.jsx';script.write_text(TEMPLATE.replace('__CONFIG__',json.dumps({'job':str(job),'assets':assets},ensure_ascii=True)),encoding='ascii')
 if args.execute:
  if sys.platform!='darwin':raise RuntimeError('Use the Windows Illustrator launcher to run the prepared JSX on Windows')
  code='on run argv\nset scriptFile to POSIX file (item 1 of argv)\ntell application id "com.adobe.illustrator"\nwith timeout of 240 seconds\ndo javascript scriptFile\nend timeout\nend tell\nend run'
  r=subprocess.run(['osascript','-',str(script)],input=code,text=True,capture_output=True,timeout=260)
  if r.returncode:raise RuntimeError(r.stderr)
 print(script)
if __name__=='__main__':main()
