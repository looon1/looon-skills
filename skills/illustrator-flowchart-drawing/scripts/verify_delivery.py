#!/usr/bin/env python3
"""Check a final bundle and create reference/round-trip difference artifacts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops


def normalized(text):
    return ''.join(text.split())


def compare_images(reference, actual, prefix):
    with Image.open(reference) as a, Image.open(actual) as b:
        a,b=a.convert('RGB'),b.convert('RGB')
        if a.size!=b.size:raise ValueError(f'Image dimensions differ: {a.size} vs {b.size}')
        diff=ImageChops.difference(a,b)
        histogram=diff.histogram()
        mae=sum((i%256)*n for i,n in enumerate(histogram))/(a.width*a.height*3)
        changed=sum(1 for p in diff.get_flattened_data() if any(p))
        diff.save(str(prefix)+'-difference.png')
        Image.blend(a,b,0.5).save(str(prefix)+'-overlay.png')
        return {'dimensions':list(a.size),'different_pixels':changed,'mean_absolute_channel_error':mae,'difference_bounds':diff.getbbox()}


def verify(output,job=None,reference=None,reopened=None):
    output=Path(output)
    audit=json.loads((output/'native-audit.json').read_text(encoding='utf-8'))
    ai=output/Path(audit['ai']).name
    if not ai.is_file() or ai.stat().st_size<100:raise ValueError('Missing native AI')
    if audit['raster'] or audit['placed']:raise ValueError('Raster artwork in native delivery')
    root=ET.parse(output/'master.svg').getroot()
    view=[float(n) for n in re.split(r'[ ,]+',root.attrib['viewBox'])]
    width,height=audit['canvas']
    if abs(view[2]/view[3]-width/height)>1e-5:raise ValueError('SVG canvas ratio differs')
    texts=[]
    for node in root.iter():
        kind=node.tag.rsplit('}',1)[-1]
        if kind=='image':raise ValueError('Master SVG contains a raster image')
        if kind=='text':texts.append(normalized(''.join(node.itertext())))
    expected=Counter(normalized(t['text']) for t in audit['text_frames'])
    if Counter(texts)!=expected:raise ValueError('Master SVG does not preserve ordinary text')
    with Image.open(output/'preview.png') as image:
        if image.size!=(round(width),round(height)):raise ValueError('PNG dimensions differ from artboard')
    formulas=json.loads((output/'formulas.json').read_text(encoding='utf-8'))
    if len(formulas)!=audit['formulas']:raise ValueError('Formula inventory/count differs')
    for item in formulas:
        source=output/item['source_file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=item['source_sha256']:raise ValueError('Formula source changed: '+item['id'])
        if not (output/item['svg_file']).is_file():raise ValueError('Missing formula outline: '+item['id'])
    if job:
        config=json.loads((Path(job)/'job.json').read_text(encoding='utf-8'))
        if config['fingerprint']!=audit['fingerprint']:raise ValueError('Delivery is from a different prepared job')
        if Counter(normalized(t['text']) for t in config['labels'])!=expected:raise ValueError('Native text differs from original manifest')
    report={'structural_checks':'passed','ai':ai.name,'canvas':audit['canvas'],'native_text_frames':len(audit['text_frames']),
            'typeset_formulas':len(formulas),'formula_semantic_review':'pending','reference_fidelity_review':'pending',
            'files':{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in [ai.name,'preview.png','master.svg','formulas.json']}}
    if reference:report['reference_comparison']=compare_images(reference,output/'preview.png',output/'reference')
    if reopened:report['save_reopen_comparison']=compare_images(output/'preview.png',reopened,output/'save-reopen')
    (output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--job-dir',type=Path)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--reopened-png',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.output,args.job_dir,args.reference,args.reopened_png),ensure_ascii=False,indent=2))
