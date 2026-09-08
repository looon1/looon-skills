import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

script = Path(__file__).with_name('prepare_job.py')
spec = importlib.util.spec_from_file_location('prepare_job', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'image.png'
        self.job, self.output = self.base/'job', self.base/'output'
        Image.new('RGB', (100, 80), (242, 238, 231)).save(self.source)

    def run_prepare(self, data=None):
        manifest=None
        if data is not None:
            manifest=self.base/'labels.json'
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
        module.prepare(self.source, self.job, self.output, manifest)

    def label(self, text='Result ≥ 20'):
        return {'text':text,'font':'ArialMT','bounds':[10,10,80,30]}

    def test_rgb_pixels_unicode_and_background(self):
        self.run_prepare()
        with Image.open(self.source) as source, Image.open(self.job/'source.tif') as tiff:
            self.assertEqual(source.tobytes(),tiff.tobytes())
        Image.open(self.source).save(self.job/'trace-preview.png')
        self.run_prepare({'labels':[self.label()], 'groups':[]})
        data=json.loads((self.job/'job.json').read_text())
        self.assertEqual(data['labels'][0]['text'],'Result ≥ 20')
        self.assertEqual(data['labels'][0]['background'],[242,238,231])
        generated=(self.job/'rebuild.jsx').read_text(encoding='ascii')
        self.assertIn('\\u2265',generated)

    def test_dense_dark_ink_is_not_chosen_as_background(self):
        self.run_prepare()
        preview=Image.open(self.source)
        preview.paste((20,20,20),(10,10,80,30))
        preview.save(self.job/'trace-preview.png')
        self.run_prepare({'labels':[self.label()]})
        result=json.loads((self.job/'job.json').read_text())
        self.assertEqual(result['labels'][0]['background'],[242,238,231])

    def test_dense_labels_inside_illustration(self):
        self.run_prepare()
        Image.open(self.source).save(self.job/'trace-preview.png')
        first = dict(self.label('H'), bounds=[20, 20, 30, 30], padding=0.5)
        second = dict(self.label('N'), bounds=[20, 32, 30, 42], padding=0.5, repair='glyphs')
        self.run_prepare({'labels':[first, second], 'groups':[{'name':'Molecule', 'bounds':[5,5,90,70]}]})
        result=json.loads((self.job/'job.json').read_text())
        self.assertEqual([x['text'] for x in result['labels']], ['H','N'])
        self.assertEqual(result['labels'][1]['repair'],'glyphs')

    def test_invalid_repair_rejected(self):
        self.run_prepare()
        Image.open(self.source).save(self.job/'trace-preview.png')
        with self.assertRaisesRegex(ValueError,'repair'):
            self.run_prepare({'labels':[dict(self.label(),repair='unknown')]})

    def test_transparency_rejected_without_conversion(self):
        Image.new('RGBA',(100,80),(1,2,3,50)).save(self.source)
        with self.assertRaisesRegex(ValueError,'opaque RGB'):self.run_prepare()

    def test_new_source_cannot_reuse_job(self):
        self.run_prepare()
        Image.new('RGB',(100,80),(1,2,3)).save(self.source)
        with self.assertRaisesRegex(ValueError,'different image'):self.run_prepare()

    def test_overlapping_text_rejected(self):
        self.run_prepare()
        Image.open(self.source).save(self.job/'trace-preview.png')
        with self.assertRaisesRegex(ValueError,'overlap'):
            self.run_prepare({'labels':[self.label(),self.label('Other')]})

    def test_outside_region_rejected(self):
        with self.assertRaisesRegex(ValueError,'outside'):
            self.run_prepare({'groups':[{'name':'Icon','bounds':[-1,0,10,10]}]})

    def test_label_requires_matching_native_preview(self):
        self.run_prepare()
        Image.new('RGB',(50,50)).save(self.job/'trace-preview.png')
        with self.assertRaisesRegex(ValueError,'dimensions'):
            self.run_prepare({'labels':[self.label()]})


if __name__=='__main__': unittest.main()
