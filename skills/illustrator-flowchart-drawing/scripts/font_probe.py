"""Resolve requested native PostScript fonts and verify weight and glyph coverage."""
import hashlib
import os
from pathlib import Path
from fontTools.ttLib import TTFont, TTCollection


def inspect_fonts(labels):
    if not labels:return []
    wanted={item['font'] for item in labels}
    roots=[Path('/Library/Fonts'),Path('/System/Library/Fonts'),Path.home()/'Library/Fonts']
    if os.name=='nt':
        roots=[Path(os.environ['WINDIR'])/'Fonts',Path(os.environ.get('LOCALAPPDATA',''))/'Microsoft/Windows/Fonts']
    found={}
    for root in roots:
        if not root.exists():continue
        for path in root.rglob('*'):
            if path.suffix.lower() not in ('.otf','.ttf','.ttc'):continue
            collection=None
            try:
                if path.suffix.lower()=='.ttc':collection=TTCollection(path,lazy=True);fonts=collection.fonts
                else:fonts=[TTFont(path,lazy=True)]
                for font in fonts:
                    names={n.toUnicode() for n in font['name'].names if n.nameID==6}
                    for name in names&wanted:
                        cmap=font.getBestCmap() or {}
                        found[name]={'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'weight':font['OS/2'].usWeightClass,'italic':bool(font['head'].macStyle&2),'cmap':set(cmap)}
                    if not collection:font.close()
            except (OSError,KeyError):continue
            finally:
                if collection:collection.close()
        if wanted<=set(found):break
    report=[]
    for label in labels:
        name=label['font']
        if name not in found:raise ValueError(f'Cannot locate font file for {name}; install/register the font before drawing')
        font=found[name]
        missing=sorted({ord(c) for c in label['text'] if not c.isspace()}-font['cmap'])
        if missing:raise ValueError(f'{name}: missing glyphs '+', '.join(f'U+{c:04X}' for c in missing))
        if label.get('weight','bold')=='bold' and font['weight']<700:raise ValueError(f'{name}: actual font weight {font["weight"]} is not bold')
        if label.get('italic') and not font['italic']:raise ValueError(f'{name}: genuine italic face required')
        report.append(dict(id=label.get('id'),postscript_name=name,**{k:v for k,v in font.items() if k!='cmap'}))
    return report
