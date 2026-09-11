import copy, importlib.util, json, tempfile, unittest, zipfile
from pathlib import Path
from xml.etree import ElementTree as E
import prepare_powerpoint as p
spec=importlib.util.spec_from_file_location('player',Path(__file__).with_name('run-powerpoint-mac.py'));player=importlib.util.module_from_spec(spec);spec.loader.exec_module(player)
class PowerPointTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.data={'width':1000,'height':700,'objects':[{'id':'label','type':'text','bounds':[20,20,300,50],'text':'Mφ · H₂O₂ · TGF-β','font_size':28},{'id':'curve','type':'path','bounds':[20,100,300,100],'commands':[['M',20,100],['C',100,100,200,200,320,200]],'stroke':'123456','arrow':True}]}
 def prepare(self):
  m=self.root/'scene.json';m.write_text(json.dumps(self.data));return p.prepare(m,self.root/'cache.pptx')
 def test_roundtrip_live_text_curves_arrow_and_aspect(self):
  r=self.prepare();self.assertEqual(r['counts'],{'text':1,'native':2,'picture':0,'groups':0});self.assertEqual(player.audit(self.root/'cache.pptx')[0]['text'],'Mφ · H₂O₂ · TGF-β')
  with zipfile.ZipFile(self.root/'cache.pptx') as z:
   s=E.fromstring(z.read('ppt/slides/slide1.xml'));self.assertEqual(len(s.findall('.//a:cubicBezTo',p.NS)),1);self.assertEqual(s.find('.//a:tailEnd',p.NS).get('type'),'triangle')
   sz=E.fromstring(z.read('ppt/presentation.xml')).find('p:sldSz',p.NS);self.assertAlmostEqual(int(sz.get('cy'))/int(sz.get('cx')),.7)
 def test_no_overwrite(self):
  self.prepare()
  with self.assertRaises(FileExistsError):self.prepare()
 def test_duplicate_names_rejected(self):
  self.data['objects'][1]['id']='label'
  with self.assertRaisesRegex(ValueError,'Duplicate'):self.prepare()
 def test_bad_geometry_rejected(self):
  self.data['objects'][0]['bounds'][0]=-1
  with self.assertRaisesRegex(ValueError,'Outside'):self.prepare()
 def test_native_mode_rejects_raster(self):
  self.data['objects'][0]['type']='image'
  with self.assertRaisesRegex(ValueError,'hybrid'):self.prepare()
 def test_hybrid_requires_raster_evidence(self):
  self.data['mode']='hybrid';self.data['objects'][0]['type']='image'
  with self.assertRaisesRegex(ValueError,'declaration'):self.prepare()
 def test_unknown_curve_rejected(self):
  self.data['objects'][1]['commands']=[['A',1,2]]
  with self.assertRaisesRegex(ValueError,'path'):self.prepare()
 def test_native_groups_keep_child_curve_and_text(self):
  children=copy.deepcopy(self.data['objects']);self.data['objects']=[{'id':'complex.batch-1','type':'group','bounds':[20,20,300,180],'children':children}]
  r=self.prepare();self.assertEqual(r['counts']['groups'],1);self.assertEqual(r['counts']['native'],2)
  with zipfile.ZipFile(self.root/'cache.pptx') as z:
   root=E.fromstring(z.read('ppt/slides/slide1.xml'));self.assertEqual(len(root.findall('.//p:grpSp',p.NS)),1);self.assertEqual(len(root.findall('.//a:cubicBezTo',p.NS)),1)
   ids=[n.get('id') for n in root.findall('.//p:cNvPr',p.NS)];self.assertEqual(len(ids),len(set(ids)))
 def test_vector_import_preserves_control_points_and_compound_parts(self):
  from import_powerpoint_vectors import convert
  asset={'id':'mouse','bounds':[100,200,200,100]}
  geom={'width':100,'height':50,'atoms':[{'fill':[10,20,30],'parts':[{'closed':True,'points':[[[0,50],[0,50],[10,45]],[[100,0],[90,5],[100,0]]]}]}]}
  r=convert(asset,geom);self.assertEqual(r[0]['fill'],'0A141E');self.assertEqual(r[0]['commands'][0],['M',100,200]);self.assertEqual(r[0]['commands'][1],['C',120,210,280,290,300,300]);self.assertEqual(r[0]['commands'][-1],['Z'])
 def test_compound_contours_stay_in_one_native_path(self):
  self.data['objects']=[{'id':'ring','type':'path','bounds':[50,50,200,200],'fill':'FFFFFF','commands':[['M',50,50],['L',250,50],['L',250,250],['L',50,250],['Z'],['M',100,100],['L',100,200],['L',200,200],['L',200,100],['Z']]}]
  self.prepare()
  with zipfile.ZipFile(self.root/'cache.pptx') as z:
   root=E.fromstring(z.read('ppt/slides/slide1.xml'));self.assertEqual(len(root.findall('.//a:pathLst/a:path',p.NS)),1);self.assertEqual(len(root.findall('.//a:moveTo',p.NS)),2)
 def test_evenodd_compound_rejected_before_export(self):
  from import_powerpoint_vectors import convert
  part={'closed':True,'points':[[[0,0],[0,0],[0,0]],[[10,10],[10,10],[10,10]]]}
  g={'width':100,'height':100,'atoms':[{'fill':[255,255,255],'fill_rule':'evenodd','parts':[part,part]}]}
  with self.assertRaisesRegex(ValueError,'winding'):convert({'id':'ring','bounds':[0,0,100,100]},g)
 def test_script_string_escaping(self):
  self.assertEqual(player.quote('x"\\\n'), '"x\\"\\\\\\n"')
if __name__=='__main__':unittest.main()
