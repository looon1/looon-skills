#!/usr/bin/env python3
"""Prepare a local Illustrator job. Does not launch or control Illustrator."""
import argparse
import json
from pathlib import Path
import shutil

from PIL import Image


def bounds(value, size, label):
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f'{label}: bounds must have four numbers')
    if any(type(v) not in (int, float) for v in value):
        raise ValueError(f'{label}: bounds must be numeric')
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
        raise ValueError(f'{label}: bounds outside the source image')
    return value


def intersects(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def color(value):
    if not isinstance(value, list) or len(value) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in value):
        raise ValueError('Colors must be three integers from 0 to 255')
    return value


def native_layout(data, size):
    if data is None:
        return None
    names=set()
    for item in data['elements']:
        if not isinstance(item.get('name'),str) or not item['name'] or item['name'] in names:
            raise ValueError('Native element names must be unique and nonempty')
        names.add(item['name'])
        if item['type'] in ('rect','ellipse'):
            bounds(item['bounds'],size,item['name'])
        elif item['type']=='path':
            if len(item['points'])<2:
                raise ValueError('Native paths need at least two anchors')
            for point in item['points']:
                if len(point) not in (1,3) or any(len(p)!=2 or any(type(x) not in (int,float) for x in p) for p in point):
                    raise ValueError('Each native point needs an anchor and optional two handles')
        else:
            raise ValueError('Native element type must be rect, ellipse or path')
        if item.get('stroke') is not None:
            color(item['stroke'])
            if type(item.get('width',2)) not in (int,float) or item.get('width',2)<=0:
                raise ValueError('Stroke width must be positive')
        if item.get('dashes') is not None and (not item['dashes'] or any(type(x) not in (int,float) or x<=0 for x in item['dashes'])):
            raise ValueError('Dash lengths must be positive')
        if item.get('arrow') and (item['type']!='path' or not item.get('stroke') or len(item['arrow'])!=2 or any(x<=0 for x in item['arrow'])):
            raise ValueError('Arrows need a stroked path and positive head dimensions')
        fill=item.get('fill')
        if isinstance(fill,list):color(fill)
        elif fill is not None:
            if len(fill['stops'])<2 or any(not 0<=s[0]<=100 for s in fill['stops']) or fill['length']<=0:
                raise ValueError('Invalid linear gradient')
            for stop in fill['stops']:color(stop[1])
    for region in data.get('regions',[]):bounds(region['bounds'],size,region['name'])
    for rule in data.get('removeTraced',[]):bounds(rule['bounds'],size,rule['group'])
    return dict(elements=data['elements'],regions=data.get('regions',[]),removeTraced=data.get('removeTraced',[]))


def prepare(source, job, output, manifest=None, editable_source=None):
    source, job, output = source.resolve(), job.resolve(), output.resolve()
    with Image.open(source) as original:
        if original.mode != 'RGB' or getattr(original, 'n_frames', 1) != 1:
            raise ValueError('Helper requires a single opaque RGB image; handle transparency/CMYK explicitly')
        original.load()
        # Deliberately omit ICC metadata; keep decoded RGB samples unchanged.
        pixels = Image.frombytes('RGB', original.size, original.tobytes())
    data = json.loads(manifest.read_text(encoding='utf-8')) if manifest else {}
    job.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    tiff = job / 'source.tif'
    if tiff.exists():
        with Image.open(tiff) as previous:
            if previous.size != pixels.size or previous.mode != 'RGB' or previous.tobytes() != pixels.tobytes():
                raise ValueError('Job belongs to a different image; choose a fresh job directory')
    else:
        pixels.save(tiff, compression='raw')
    with Image.open(tiff) as check:
        if check.mode != 'RGB' or check.size != pixels.size or check.tobytes() != pixels.tobytes():
            raise ValueError('TIFF pixel verification failed')

    labels, groups, repair_boxes = [], [], []
    preview = None
    if any(item.get('background') is None for item in data.get('labels',[])):
        preview = Image.open(job / 'trace-preview.png').convert('RGB')
        if preview.size != pixels.size:
            raise ValueError('Trace preview dimensions differ from source')
    for item in data.get('labels', []):
        b = bounds(item['bounds'], pixels.size, item['text'])
        if not isinstance(item['text'], str) or not item['text'] or '\n' in item['text'] or '\r' in item['text']:
            raise ValueError('Each label must contain one nonempty line')
        if not isinstance(item['font'], str) or not item['font']:
            raise ValueError('Each label needs an Illustrator PostScript font name')
        padding = item.get('padding', 3)
        if type(padding) not in (int, float) or not 0 <= padding <= 10:
            raise ValueError('Text padding must be between 0 and 10 pixels')
        repair = bounds([b[0]-padding, b[1]-padding, b[2]+padding, b[3]+padding], pixels.size, item['text']+' repair')
        if editable_source is None and any(intersects(repair, other) for other in repair_boxes):
            raise ValueError('Text repair areas overlap; adjust label bounds')
        repair_boxes.append(repair)
        bg = item.get('background')
        if bg is None:
            crop = preview.crop(tuple(round(v) for v in repair))
            candidates = [pair for pair in crop.getcolors(crop.width * crop.height) if sum(pair[1]) > 384]
            if not candidates:
                raise ValueError('No light background found; specify background explicitly')
            bg = list(max(candidates, key=lambda pair: pair[0])[1])
        method = item.get('repair', 'rectangle')
        if method not in ('rectangle', 'glyphs'):
            raise ValueError('Text repair must be rectangle or glyphs')
        labels.append(dict(text=item['text'], bounds=b, font=item['font'], background=color(bg), color=color(item.get('color', [20, 20, 20])), repair=method, padding=padding))
    for item in data.get('groups', []):
        b = bounds(item['bounds'], pixels.size, item['name'])
        if any(intersects(b, other['bounds']) for other in groups):
            raise ValueError('Illustration regions overlap another region')
        groups.append(dict(name=item['name'], bounds=b))
    config = dict(job=job.as_posix(), output=output.as_posix(), width=pixels.width, height=pixels.height,
                  labels=labels, groups=groups, preset=data.get('preset'))
    if data.get('nativeLayout') is not None:
        config['nativeLayout']=native_layout(data['nativeLayout'],pixels.size)
    if editable_source is not None:
        target=job/'source.ai'
        if target.exists() and target.read_bytes()!=editable_source.read_bytes():
            raise ValueError('Editable source changed; use a new job directory')
        if not target.exists():shutil.copy2(editable_source,target)
    native = Path(__file__).with_name('native.jsx').read_text(encoding='utf-8')
    for stage in ['inspect', 'trace', 'rebuild', 'structure', 'verify', 'live']:
        script = native.replace('__CONFIG__', json.dumps(config, ensure_ascii=True)).replace('__STAGE__', json.dumps(stage))
        (job / f'{stage}.jsx').write_text(script, encoding='ascii')
    (job / 'job.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prepared {pixels.width}x{pixels.height}; {len(labels)} labels; {len(groups)} groups. TIFF pixels verified.')
    print(f'Execute the JSX files in Illustrator from: {job}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--job-dir', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--editable-source', type=Path, help='Verified AI to recompose with native geometry in a fresh output directory')
    args = parser.parse_args()
    prepare(args.source, args.job_dir, args.output_dir, args.manifest,args.editable_source)
