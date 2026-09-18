"""Conservative XML scope check for stable-ID SVG edits; no visual acceptance."""
import argparse
import copy
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

SVG = '{http://www.w3.org/2000/svg}'


def load(path):
    source = Path(path).read_text(encoding='utf-8-sig')
    if re.search(r'<!DOCTYPE|<!ENTITY', source, re.I):
        raise ValueError('DTD/entity input is unsupported')
    root = ET.fromstring(source)
    if root.tag != SVG + 'svg':
        raise ValueError('Expected an SVG namespace root')
    index = {}
    for node in root.iter():
        ident = node.get('id')
        if ident:
            if ident in index:
                raise ValueError('Duplicate ID: ' + ident)
            index[ident] = node
    return root, index


def serialize(node):
    node = copy.deepcopy(node)
    node.tail = None
    return ET.tostring(node, encoding='unicode')


def compare(before, after, allowed):
    result = {'scope_passed': False, 'target_changed': {}, 'target_verified': None,
              'issues': [], 'unchecked': ['visual improvement', 'part membership',
                                         'Illustrator behavior', 'SVG safety']}
    try:
        if not allowed or len(set(allowed)) != len(allowed):
            raise ValueError('Supply distinct allowed IDs')
        protected, resources = [], []
        selected = []
        for path in (before, after):
            root, index = load(path)
            local = set()
            selected.append({})
            for ident in allowed:
                if ident not in index:
                    raise ValueError('Missing allowed ID: ' + ident)
                node = index[ident]
                if node is root or node.tag in {SVG + 'defs', SVG + 'style'}:
                    raise ValueError('Cannot allow document root or shared resources')
                descendants = list(node.iter())
                if any(n is not node and n.get('id') in allowed for n in descendants):
                    raise ValueError('Allowed scopes overlap')
                local.update(descendants)
                selected[-1][ident] = serialize(node)
            local_ids = {n.get('id') for n in local if n.get('id')}
            resources.append([serialize(n) for n in root.iter() if n.tag == SVG + 'defs'])
            for node in root.iter():
                if node.tag in {SVG + t for t in ('style', 'script', 'animate', 'animateTransform', 'set')}:
                    raise ValueError('Stylesheet, script or animation needs dependency review')
                for key, value in node.attrib.items():
                    if key.rsplit('}', 1)[-1] == 'href' and not value.startswith('#'):
                        raise ValueError('External resource needs dependency review')
                    if node not in local:
                        if any('#' + ident in value for ident in local_ids):
                            raise ValueError('Protected object may reference edited content')
            # Keep the target slot and its tail, so reordering/removal remains observable.
            for ident in allowed:
                node = index[ident]
                tail, tag = node.tail, node.tag
                node.clear()
                node.tag, node.tail = tag, tail
                node.set('id', ident)
            protected.append(serialize(root))
        result['target_changed'] = {i: selected[0][i] != selected[1][i] for i in allowed}
        if protected[0] != protected[1]:
            result['issues'].append('Content outside allowed scopes changed')
        if resources[0] != resources[1]:
            result['issues'].append('Shared definitions changed')
        result['scope_passed'] = not result['issues']
    except (OSError, ValueError, ET.ParseError) as exc:
        result['issues'].append(str(exc))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('--allow', action='append', required=True)
    args = parser.parse_args()
    report = compare(args.before, args.after, args.allow)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['scope_passed'] else 1)
