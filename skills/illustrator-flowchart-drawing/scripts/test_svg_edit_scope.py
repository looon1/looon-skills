"""Regression cases for edits that accidentally affect protected artwork."""
from pathlib import Path
import tempfile
import unittest
from check_svg_edit_scope import compare

BASE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
<g id="scene"><g id="cell"><circle id="membrane" r="20"/>
<circle id="nucleus" r="8"/></g><text id="label">ROS</text></g></svg>'''


class EditScopeTests(unittest.TestCase):
    def check(self, after, before=BASE, allowed=('cell',)):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / 'a.svg', Path(directory) / 'b.svg'
            a.write_text(before, encoding='utf-8')
            b.write_text(after, encoding='utf-8')
            return compare(a, b, list(allowed))

    def test_local_edit_is_not_visual_acceptance(self):
        result = self.check(BASE.replace('r="8"', 'r="9"'))
        self.assertTrue(result['scope_passed'])
        self.assertTrue(result['target_changed']['cell'])
        self.assertIsNone(result['target_verified'])

    def test_unchanged_target(self):
        result = self.check(BASE)
        self.assertTrue(result['scope_passed'])
        self.assertFalse(result['target_changed']['cell'])

    def test_protected_label_and_parent(self):
        for after in (BASE.replace('ROS', 'NETosis'),
                      BASE.replace('id="scene"', 'id="scene" transform="translate(5)"')):
            self.assertFalse(self.check(after)['scope_passed'])

    def test_target_slot_cannot_move(self):
        after = BASE.replace('<text id="label">ROS</text>', '')
        after = after.replace('<g id="cell">', '<text id="label">ROS</text><g id="cell">')
        self.assertFalse(self.check(after)['scope_passed'])

    def test_shared_definition_inside_target(self):
        before = BASE.replace('<g id="cell">', '<g id="cell"><defs><path id="symbol" d="M0 0L1 1"/></defs>')
        self.assertFalse(self.check(before.replace('L1 1', 'L2 2'), before)['scope_passed'])

    def test_reference_to_target_needs_review(self):
        before = BASE.replace('</svg>', '<use href="#nucleus"/></svg>')
        self.assertFalse(self.check(before.replace('r="8"', 'r="9"'), before)['scope_passed'])

    def test_css_needs_review(self):
        before = BASE.replace('</svg>', '<style>circle {fill:red}</style></svg>')
        self.assertFalse(self.check(before, before)['scope_passed'])

    def test_bad_scope_or_input(self):
        for allowed in ((), ('missing',), ('cell', 'cell'), ('cell', 'nucleus')):
            self.assertFalse(self.check(BASE, allowed=allowed)['scope_passed'])
        for after in ('<svg>', BASE.replace('id="label"', 'id="cell"')):
            self.assertFalse(self.check(after)['scope_passed'])


if __name__ == '__main__':
    unittest.main()
