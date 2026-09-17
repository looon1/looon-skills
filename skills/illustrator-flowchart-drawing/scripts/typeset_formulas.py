#!/usr/bin/env python3
"""Typeset complete TeX expressions; return native compound geometry, never traced glyphs."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont


def run(command, cwd=None):
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(f'{command[0]} failed:\n{(result.stdout + result.stderr)[-3000:]}')
    return result.stdout + result.stderr


class Contours(BasePen):
    def __init__(self):
        super().__init__(None)
        self.parts = []
        self.current = None

    def _moveTo(self, p):
        self.current = {'closed': False, 'points': [[list(p), list(p), list(p)]]}
        self.parts.append(self.current)

    def _lineTo(self, p):
        self.current['points'].append([list(p), list(p), list(p)])

    def _curveToOne(self, a, b, p):
        self.current['points'][-1][2] = list(a)
        self.current['points'].append([list(p), list(b), list(p)])

    def _closePath(self):
        points = self.current['points']
        if len(points) > 1 and points[0][0] == points[-1][0]:
            points[0][1] = points.pop()[1]
        self.current['closed'] = True

    def _endPath(self):
        pass


def outline_geometry(path):
    root = ET.parse(path).getroot()
    view = list(map(float, root.attrib['viewBox'].split()))
    atoms = []
    for node in root.iter():
        kind = node.tag.rsplit('}', 1)[-1]
        if node.get('transform'):
            raise ValueError('Unexpected transformed formula SVG; normalize before importing')
        if kind in ('svg', 'g', 'defs'):
            continue
        if kind == 'path':
            pen = Contours()
            parse_path(node.attrib['d'], pen)
            parts = pen.parts
        elif kind == 'rect':
            x, y, w, h = (float(node.get(k, 0)) for k in ('x', 'y', 'width', 'height'))
            parts = [{'closed': True, 'points': [[list(p)] * 3 for p in ((x,y),(x+w,y),(x+w,y+h),(x,y+h))]}]
        else:
            raise ValueError(f'Formula SVG must contain only vector outlines, found {kind}')
        if parts:
            atoms.append({'parts': parts, 'evenodd': node.get('fill-rule') == 'evenodd'})
    if not atoms or view[2] <= 0 or view[3] <= 0:
        raise ValueError('Empty formula output')
    return view, atoms


def typeset(items, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if not items:
        (output / 'formulas.json').write_text('[]\n', encoding='utf-8')
        return []
    for binary in ('xelatex', 'dvisvgm', 'kpsewhich'):
        if not shutil.which(binary):
            raise RuntimeError(f'Missing {binary}; install TeX Live with unicode-math, standalone and XITS')
    versions = {name: run([name, '--version']).splitlines()[0] for name in ('xelatex', 'dvisvgm')}
    results, ids = [], set()
    for item in items:
        identifier = item['id']
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', identifier) or identifier in ids:
            raise ValueError('Formula ids must be unique safe filenames')
        ids.add(identifier)
        expression = item['tex']
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError('Formula needs a complete TeX expression')
        if re.search(r'[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]', expression):
            raise ValueError('Use structural TeX superscripts/subscripts')
        # Inputs are expressions, not arbitrary TeX programs or file-loading macros.
        if re.search(r'\\(?:input|include\w*|write\w*|open\w*|read\w*|directlua|special|catcode|csname|def|let|usepackage|documentclass|begin\{document)', expression):
            raise ValueError('Formula source must be a math expression without external I/O or document commands')
        weight = item.get('weight', 'bold')
        if weight not in ('bold', 'regular'):
            raise ValueError('Math weight must be bold or regular')
        font_name = item.get('math_font','XITSMath-Bold.otf' if weight == 'bold' else 'XITSMath-Regular.otf')
        text_font_name = item.get('text_font','XITS-Bold.otf' if weight == 'bold' else 'XITS-Regular.otf')
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]+\.(?:otf|ttf)',v) for v in (font_name,text_font_name)):raise ValueError('Specify font filenames, not TeX commands')
        font_path = Path(run(['kpsewhich', font_name]).strip())
        with TTFont(font_path) as font:
            font_weight = font['OS/2'].usWeightClass
            if 'MATH' not in font or (weight == 'bold' and font_weight < 700):
                raise ValueError('Selected font lacks real bold mathematical glyphs')
        text_font_path=Path(run(['kpsewhich',text_font_name]).strip())
        with TTFont(text_font_path) as text_font:
            if weight=='bold' and text_font['OS/2'].usWeightClass<700:raise ValueError('Upright math text needs a real bold font')
            text_font_weight=text_font['OS/2'].usWeightClass
        size = float(item.get('font_size', 18))
        if not 1 <= size <= 500:
            raise ValueError('Formula font_size must be between 1 and 500 pt')
        folder = output / 'formulas' / identifier
        folder.mkdir(parents=True, exist_ok=True)
        source = ('\\documentclass[border=0pt]{standalone}\n\\usepackage{unicode-math}\n'
                  f'\\setmainfont{{{text_font_name}}}\n\\setmathfont{{{font_name}}}\n\\begin{{document}}\n'
                  f'\\fontsize{{{size}}}{{{size*1.2}}}\\selectfont\n'
                  '$\\displaystyle ' + expression + '$\n\\end{document}\n')
        (folder / 'source.tex').write_text(source, encoding='utf-8')
        log = run(['xelatex', '-no-pdf', '-no-shell-escape', '-halt-on-error', '-interaction=nonstopmode', '-recorder', 'source.tex'], folder)
        if 'Missing character:' in log:
            raise ValueError(f'Missing mathematical glyph in {identifier}')
        run(['dvisvgm', '--no-fonts=1', '--exact-bbox', '--bbox=min', '--output=outline.svg', 'source.xdv'], folder)
        view, atoms = outline_geometry(folder / 'outline.svg')
        x0,y0,x1,y1 = item['bounds']
        # Explicit font size is authoritative. Otherwise fit the complete formula uniformly.
        scale = 1 if 'font_size' in item else min((x1-x0)/view[2], (y1-y0)/view[3])
        width, height = view[2]*scale, view[3]*scale
        if width > x1-x0+0.1 or height > y1-y0+0.1:
            raise ValueError(f'{identifier}: formula exceeds bounds; adjust source, font_size or bounds')
        for atom in atoms:
            for part in atom['parts']:
                part['points'] = [[[x0+(p[0]-view[0])*scale, y0+(p[1]-view[1])*scale] for p in point] for point in part['points']]
        result = dict(item, name='Formula '+identifier, atoms=atoms, color=item.get('color',[20,20,20]),
                      actual_bounds=[x0,y0,x0+width,y0+height], source_file=f'formulas/{identifier}/source.tex',
                      svg_file=f'formulas/{identifier}/outline.svg', source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                      engine=versions, font=dict(file=font_name, weight=font_weight, sha256=hashlib.sha256(font_path.read_bytes()).hexdigest()),
                      text_font=dict(file=text_font_name,weight=text_font_weight,sha256=hashlib.sha256(text_font_path.read_bytes()).hexdigest()),
                      edit_mode='typeset-vector-outlines-with-source', review_status='pending-reference-review')
        results.append(result)
        # Only reproducible deliverables belong in the output package.
        for suffix in ('aux', 'log', 'xdv', 'fls'):
            (folder / ('source.'+suffix)).unlink(missing_ok=True)
    (output/'formulas.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='atoms'} for r in results], ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    return results


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(typeset(json.loads(args.manifest.read_text(encoding='utf-8')), args.output_dir),ensure_ascii=False))
