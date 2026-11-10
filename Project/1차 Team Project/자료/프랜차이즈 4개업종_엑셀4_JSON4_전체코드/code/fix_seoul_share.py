"""서울/전국 값이 있는 행의 서울비중 수식 캐시를 갱신한다. 상수·수식·서식은 유지한다."""
from pathlib import Path
from zipfile import ZipFile
import re,json,math
from preserve_workbooks import read_cells,sheet_paths,_raw_cells,save_json,export_json
ROOT=Path(__file__).resolve().parents[1]
def fix(root=ROOT):
 reports=[];plan=json.loads((root/'보완계획.json').read_text(encoding='utf-8'))
 for item in plan:
  path=root/'excel'/item['filename'];changes=[]
  with ZipFile(path) as z:
   parts={i.filename:z.read(i.filename) for i in z.infolist()};infos=z.infolist();s=next(s for s in read_cells(z) if s['name']=='03_지역집계');part=sheet_paths(z)[s['name']]
  text=parts[part].decode();original=text
  for coord,c in s['cells'].items():
   if not re.fullmatch(r'G\d+',coord) or c['type']!='formula':continue
   row=int(coord[1:]);a=s['cells'].get(f'C{row}',{}).get('value');b=s['cells'].get(f'E{row}',{}).get('value')
   if not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or b<=0:continue
   result=a/b;old=c.get('original_cached_value')
   if isinstance(old,(int,float)) and math.isclose(old,result,abs_tol=1e-14):continue
   oldxml=_raw_cells(text)[coord];new=re.sub(r'\s+t="[^"]*"','',oldxml,count=1)
   new=re.sub(r'<v(?:\s[^>]*)?(?:/>|>[\s\S]*?</v>)','',new);new=new.replace('</c>',f'<v>{result:.17g}</v></c>')
   text=text.replace(oldxml,new,1);changes.append({'cell':coord,'formula':c['value'],'seoul_count':a,'national_count':b,'ratio':result,'display_percent':f'{result:.1%}'})
  if changes:
   tmp=path.with_suffix('.tmp')
   with ZipFile(tmp,'w') as out:
    for i in infos:out.writestr(i,text.encode() if i.filename==part else parts[i.filename])
   tmp.replace(path)
   # 수정 대상 셀만 복원하면 기존 XML과 완전히 같은지 검증한다.
   before=_raw_cells(original);after=_raw_cells(text);restored=text
   for c in changes:restored=restored.replace(after[c['cell']],before[c['cell']],1)
   assert restored==original
  export_json(path,root/'json'/(path.stem+'.json'),item['patches'],item['filename'])
  reports.append({'filename':path.name,'formula_cache_updates':changes,'original_constants_changed':0,'formula_text_changed':0,'format_changed':0})
 save_json(reports,root/'서울비중_수정검증.json')
 from finalize_json import finalize
 finalize(root)
 for p in (root/'json').glob('*.json'):
  o=json.loads(p.read_text(encoding='utf-8'));r=o['regional_aggregation'];r['columns'].append('seoul_share')
  for row in r['data']:row.append(row[0]/row[2] if isinstance(row[0],(int,float)) and isinstance(row[2],(int,float)) and row[2]>0 else None)
  o['description']['formula_cache']='서울비중은 서울/전국 값이 있는 모든 행의 저장 계산결과까지 확인·갱신. 다른 수식 캐시는 보존.';save_json(o,p)
 return reports
if __name__=='__main__':
 report=fix();print('서울비중 계산 결과 갱신',sum(len(r['formula_cache_updates']) for r in report))
