from pathlib import Path
import unittest,json
from zipfile import ZipFile
from preserve_workbooks import verify_preservation,read_cells
from build_region_plan import build
ROOT=Path(__file__).resolve().parents[1]
class RegionTests(unittest.TestCase):
 def test_preservation(self):
  for item in json.loads((ROOT/'보완계획.json').read_text()):
   with ZipFile(ROOT/'original'/item['filename']) as z:before=read_cells(z)
   with ZipFile(ROOT/'excel'/item['filename']) as z:after=read_cells(z)
   for old,new in zip(before,after):
    for coord,cell in old['cells'].items():
     if cell['value'] is not None:
      self.assertEqual(cell['value'],new['cells'][coord]['value']);self.assertEqual(cell['style_id'],new['cells'][coord]['style_id'])

 def test_counts_and_years(self):
  p,m,c=build(ROOT/'original',ROOT/'evidence');self.assertEqual(sum(len(i['patches']) for i in p),30);self.assertEqual(len(m),21)
  self.assertEqual(sum(a['year']==2024 for i in p for a in i['patches']),27);self.assertEqual(sum(a['year']==2025 for i in p for a in i['patches']),3)
 def test_all_cells_json_match(self):
  for f in (ROOT/'json').glob('*.json'):
   o=json.loads(f.read_text())
   with ZipFile(ROOT/'excel'/o['source_filename']) as z:self.assertEqual(o['sheets'],read_cells(z))
 def test_unchanged_workbooks(self):
  for ind in ['커피','치킨']:
   f=f'프랜차이즈_{ind}_창업비용_매출_분석.xlsx';self.assertEqual((ROOT/'original'/f).read_bytes(),(ROOT/'excel'/f).read_bytes())
 def test_actual_values(self):
  for f in (ROOT/'json').glob('*.json'):
   o=json.loads(f.read_text());r=o['regional_aggregation'];d={tuple(k):v for k,v in zip(r['index'],r['data'])}
   if '_이미용_' in f.name:self.assertEqual(d[(2024,'이미용','에이바헤어')][:3],[130,110,320])
   if '_편의점_' in f.name:self.assertEqual(d[(2025,'편의점','GS25')][:3],[3128,5001,17888]);self.assertEqual(d[(2024,'편의점','CU')][:3],[2861,4961,18255])
 def test_ratio_cache_matches_inputs(self):
  import math
  checked=0
  for p in (ROOT/'excel').glob('*.xlsx'):
   with ZipFile(p) as z:s=next(s for s in read_cells(z) if s['name']=='03_지역집계')
   for r in range(3,13):
    a=s['cells'].get(f'C{r}',{}).get('value');b=s['cells'].get(f'E{r}',{}).get('value')
    if isinstance(a,(int,float)) and isinstance(b,(int,float)) and b>0:
     self.assertTrue(math.isclose(s['cells'][f'G{r}']['original_cached_value'],a/b,abs_tol=1e-14));checked+=1
  self.assertEqual(checked,31)
if __name__=='__main__':unittest.main()
