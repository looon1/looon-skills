import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from prepare_job import prepare, bounds, native_layout
from typeset_formulas import outline_geometry, typeset
from verify_delivery import compare_images


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'reference.png';Image.new('RGB',(200,150),'white').save(self.source)
        self.job,self.output=self.root/'job',self.root/'output'

    def prepare(self,data):
        manifest=self.root/'manifest.json';manifest.write_text(json.dumps(data))
        prepare(self.source,self.job,self.output,manifest,check_fonts=False)
        return json.loads((self.job/'job.json').read_text(encoding='utf-8'))

    def test_multiline_baseline_rotation_and_font_size_survive(self):
        label=dict(id='label-a',text='First\nSecond α',font='Verified-Bold',font_size=18,baseline=[20,45],rotation=30,align='center',leading=24,bounds=[5,10,195,100],repair='none')
        result=self.prepare({'labels':[label]})['labels'][0]
        for key in ('text','font_size','baseline','rotation','align','leading'):self.assertEqual(label[key],result[key])
        self.assertTrue((self.job/'compose.jsx').read_bytes().isascii())

    def test_explicit_utf8_survives_windows_legacy_locale(self):
        original=Path.read_text
        def legacy_read(path,*args,**kwargs):
            if not args:kwargs.setdefault('encoding','cp1252')
            return original(path,*args,**kwargs)
        with patch.object(Path,'read_text',legacy_read):
            result=self.prepare({'labels':[dict(text='中文 ≥ α',font='Verified-Bold',bounds=[5,5,190,100],repair='none')]})
        self.assertEqual(result['labels'][0]['text'],'中文 ≥ α')

    def test_no_text_does_not_require_placeholder(self):
        result=self.prepare({'labels':[],'nativeLayout':{'elements':[]}})
        self.assertEqual(result['labels'],[])
        self.assertEqual(json.loads((self.output/'formulas.json').read_text(encoding='utf-8')),[])

    def test_no_repair_allows_overlapping_label_regions(self):
        label=dict(text='First',font='Verified-Bold',bounds=[1,1,180,100],padding=0,repair='none')
        self.assertEqual(len(self.prepare({'labels':[label,dict(label,text='Second') ]})['labels']),2)

    def test_duplicate_ids_rejected(self):
        label=dict(id='same',text='a',font='Verified-Bold',bounds=[1,1,180,100],padding=0,repair='none')
        with self.assertRaisesRegex(ValueError,'unique'):self.prepare({'labels':[label,label]})

    def test_invalid_text_metrics_rejected(self):
        label=dict(text='a',font='Verified-Bold',bounds=[5,5,180,100],repair='none')
        for field,value in [('font_size',0),('rotation',float('nan')),('leading',-2)]:
            with self.subTest(field=field),self.assertRaises(ValueError):self.prepare({'labels':[dict(label,**{field:value})]})

    def test_nonfinite_geometry_rejected(self):
        with self.assertRaises(ValueError):bounds([0,0,float('inf'),100],(200,150),'bad')
        with self.assertRaises(ValueError):native_layout({'elements':[{'type':'path','name':'bad','points':[[[0,0]],[[float('nan'),3]]]}]},(200,150))

    def test_arrow_rejects_undefined_terminal_direction(self):
        with self.assertRaisesRegex(ValueError,'terminal tangent'):
            native_layout({'elements':[{'type':'path','name':'bad','points':[[[1,1]],[[1,1]]],'stroke':[0,0,0],'arrow':[10,8]}]},(200,150))

    def test_no_repair_can_touch_canvas_edge(self):
        result=self.prepare({'labels':[{'text':'Edge','font':'Verified-Bold','bounds':[0,0,200,100],'repair':'none'}]})
        self.assertEqual(result['labels'][0]['padding'],0)

    def test_changed_live_job_rejected_before_deliverable_write(self):
        data={'labels':[]};config=self.prepare(data)
        (self.job/'live-session.json').write_text(json.dumps({'fingerprint':config['fingerprint']}))
        before=(self.output/'formulas.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'Active live job changed'):self.prepare({'labels':[],'playback':{'delay_ms':100}})
        self.assertEqual((self.output/'formulas.json').read_bytes(),before)

    def test_compound_holes_and_quadratic_curves_remain_contours(self):
        svg=self.root/'ring.svg';svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path fill-rule="evenodd" d="M0 0H100V100H0Z M20 20Q50 5 80 20V80H20Z"/></svg>')
        view,atoms=outline_geometry(svg)
        self.assertEqual(len(atoms),1);self.assertEqual(len(atoms[0]['parts']),2);self.assertTrue(atoms[0]['evenodd'])
        self.assertTrue(all(p['closed'] for p in atoms[0]['parts']))
        self.assertNotEqual(atoms[0]['parts'][1]['points'][0][0],atoms[0]['parts'][1]['points'][0][2])

    def test_formula_raster_is_rejected(self):
        svg=self.root/'bad.svg';svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><image href="fake.png"/></svg>')
        with self.assertRaisesRegex(ValueError,'only vector'):outline_geometry(svg)

    def test_comparison_detects_single_channel_pixel_change(self):
        other=self.root/'other.png';im=Image.open(self.source);im.putpixel((5,7),(254,255,255));im.save(other)
        result=compare_images(self.source,other,self.root/'qa')
        self.assertEqual(result['different_pixels'],1)
        self.assertGreater(result['mean_absolute_channel_error'],0)

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('dvisvgm'),'TeX engine integration needs TeX Live')
    def test_real_structured_math_and_bold_upright_font(self):
        result=typeset([{'id':'F001','tex':r'\frac{\hat{x}_i+\alpha}{\beta}=\sum_{i=1}^{n}\mathrm{H}_2','bounds':[0,0,400,150]}],self.output)[0]
        self.assertGreaterEqual(result['font']['weight'],700)
        self.assertGreaterEqual(result['text_font']['weight'],700)
        self.assertTrue(any(len(a['parts'])>1 for a in result['atoms']))
        self.assertTrue((self.output/result['source_file']).exists())
        self.assertEqual(result['edit_mode'],'typeset-vector-outlines-with-source')

    @unittest.skipUnless(shutil.which('xelatex') and shutil.which('dvisvgm'),'TeX engine integration needs TeX Live')
    def test_missing_glyph_cannot_be_delivered_as_success(self):
        with self.assertRaisesRegex(ValueError,'Missing mathematical glyph'):
            typeset([{'id':'F001','tex':'\U0001f984','bounds':[0,0,400,150]}],self.output)


if __name__=='__main__':unittest.main()
