#!/usr/bin/env python3
"""Read-only ZIP inputs; fail closed on manifest/geometry/identity errors."""
import argparse, collections, csv, hashlib, json, math, platform, shutil, zipfile
from pathlib import Path
import shapely
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.validation import explain_validity

def sha(b): return hashlib.sha256(b).hexdigest()
def dump(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def hidden(n): return any(p.startswith('.') for p in Path(n).parts)
def main():
 p=argparse.ArgumentParser();p.add_argument('--stores-zip',required=True);p.add_argument('--areas',required=True);p.add_argument('--output',required=True);args=p.parse_args()
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 if any((out/n).exists() for n in ['store_area_mapping.csv','store_area_summary.json']): raise RuntimeError('Use an empty output directory')
 z=zipfile.ZipFile(args.stores_zip);names=[i.filename for i in z.infolist() if not i.is_dir() and not hidden(i.filename)]
 assert len(names)==len(set(names)), 'Duplicate ZIP members'
 manifest=json.loads(z.read('manifest.json')); inputs=[]; cache={};ignored=[i.filename for i in z.infolist() if hidden(i.filename)]
 for f in manifest['files']:
  n=f['filename']
  if hidden(n):continue
  b=z.read(n);assert sha(b)==f['sha256'],f'Hash mismatch: {n}'
  count=None
  if n.endswith('.json'):
   data=json.loads(b);count=len(data);assert f['records'] is None or count==f['records'],n
  inputs.append({'filename':n,'records':count,'sha256':sha(b),'manifest_verified':True})
 declared={f['filename'] for f in manifest['files'] if not hidden(f['filename'])}
 assert not (set(names)-declared-{'manifest.json'}), 'Undeclared ZIP files'
 inputs.append({'filename':'manifest.json','records':None,'sha256':sha(z.read('manifest.json'))})
 b=Path(args.areas).read_bytes();areas=json.loads(b);assert len(areas)==1643
 inputs.append({'filename':Path(args.areas).name,'records':len(areas),'sha256':sha(b)})
 ids=[];geoms=[];errors=[];types=collections.Counter();holes=0
 for r in areas:
  f=r['fields'];aid=f['id'];ids.append(aid)
  try:
   assert r['model']=='CommercialArea'
   assert f['version']=='project-preview-20261103' and f['verified'] is False and f['effective_on'] is None
   raw=f['boundary'];assert raw['type'] in ('Polygon','MultiPolygon')
   polys=[raw['coordinates']] if raw['type']=='Polygon' else raw['coordinates']
   for rings in polys:
    for ring in rings:
     assert len(ring)>=4 and ring[0]==ring[-1], 'Unclosed/short ring'
     assert all(len(x)==2 and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in x) and -180<=x[0]<=180 and -90<=x[1]<=90 for x in ring),'Invalid position'
   g=shape(raw);assert not g.is_empty and g.is_valid, explain_validity(g)
   types[g.geom_type]+=1;holes+=sum(len(x)-1 for x in polys);geoms.append(g)
  except Exception as e:errors.append({'area_id':aid,'error':str(e)})
 dump(out/'geometry_validation.json',{'areas':len(areas),'errors':errors,'types':dict(types),'interior_rings':holes})
 assert not errors,'Geometry errors: final matching stopped; see geometry_validation.json'
 assert len(ids)==len(set(ids)),'Duplicate area ID'
 tree=STRtree(geoms);counts=collections.Counter({x:0 for x in ['matched','overlap','boundary','outside','invalid_coordinate']});per={str(i):0 for i in ids};seen=set();source_ids={f['fields']['id'] for f in json.loads(z.read('10_public_store_source.json'))};file_counts={};input_digest=hashlib.sha256();total=0
 storefiles=[n for n in manifest['process_order'] if n.startswith('07_public_stores_') and not hidden(n)]
 assert set(storefiles)=={n for n in names if n.startswith('07_public_stores_')}
 with (out/'store_area_mapping.csv').open('w',encoding='utf-8-sig',newline='') as mf,(out/'store_area_review.csv').open('w',encoding='utf-8-sig',newline='') as rf:
  mw=csv.writer(mf);rw=csv.writer(rf);mw.writerow(['public_store_id','source_id','external_id','area_id','status']);rw.writerow(['public_store_id','status','candidate_area_ids','reason'])
  for n in storefiles:
   rows=json.loads(z.read(n));file_counts[n]=len(rows)
   for r in rows:
    assert r['model']=='PublicStore';f=r['fields'];sid=f['id'];src=f['source_id'];ext=f['external_id']
    assert isinstance(sid,(int,str)) and not isinstance(sid,bool) and sid not in seen;seen.add(sid)
    assert src in source_ids and isinstance(ext,str) and f['reference_on']=='2026-11-03'
    identity=[str(sid),str(src),ext];input_digest.update((json.dumps(identity,ensure_ascii=False)+'\n').encode())
    inside=[];touch=[];invalid=None
    try:
     xx=f['longitude'];yy=f['latitude'];assert not isinstance(xx,bool) and not isinstance(yy,bool)
     x=float(xx);y=float(yy);assert math.isfinite(x) and math.isfinite(y) and -180<=x<=180 and -90<=y<=90
    except (ValueError,TypeError,KeyError,AssertionError):invalid='missing/non-numeric/non-finite/out-of-range longitude or latitude'
    if invalid:status='invalid_coordinate'
    else:
     pt=Point(x,y)
     for j in tree.query(pt):
      g=geoms[j]
      if g.touches(pt):touch.append(ids[j])
      elif g.contains(pt):inside.append(ids[j])
     inside.sort();touch.sort()
     status='boundary' if touch else 'overlap' if len(inside)>1 else 'matched' if len(inside)==1 else 'outside'
    area=inside[0] if status=='matched' else '';mw.writerow([sid,src,ext,area,status]);counts[status]+=1;total+=1
    if status=='matched':per[str(area)]+=1
    else:rw.writerow([sid,status,json.dumps(sorted(set(inside+touch)),ensure_ascii=False),json.dumps({'interior_area_ids':inside,'boundary_area_ids':touch,'detail':invalid or ('no containing or touching polygon' if status=='outside' else status)},ensure_ascii=False)])
   print(n,len(rows),flush=True)
 assert total==manifest['output_stores']==manifest['input_rows']==554092
 # Independent CSV readback: row identities/order, uniqueness, statuses and grouped totals.
 read_digest=hashlib.sha256();csv_seen=set();read_counts=collections.Counter();read_per=collections.Counter();review_ids=set()
 with (out/'store_area_mapping.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   assert r['public_store_id'] not in csv_seen;csv_seen.add(r['public_store_id']);read_digest.update((json.dumps([r['public_store_id'],r['source_id'],r['external_id']],ensure_ascii=False)+'\n').encode());read_counts[r['status']]+=1
   if r['status']=='matched':assert r['area_id'] in per;read_per[r['area_id']]+=1
   else:assert r['area_id']==''
 with (out/'store_area_review.csv').open(encoding='utf-8-sig',newline='') as f:
  for r in csv.DictReader(f):
   assert r['status']!='matched' and r['public_store_id'] not in review_ids;review_ids.add(r['public_store_id']);assert isinstance(json.loads(r['candidate_area_ids']),list)
 assert input_digest.digest()==read_digest.digest() and len(csv_seen)==total and read_counts==counts
 assert sum(per.values())==counts['matched'] and all(read_per[k]==v for k,v in per.items())
 assert len(review_ids)==total-counts['matched'] and review_ids<=csv_seen
 summary={'input_files':inputs,'input_store_counts':file_counts,'total_input':total,'total_processed':total,'area_count':len(ids),'status_counts':dict(counts),'matched_by_area_id':per,'coordinate_errors':counts['invalid_coordinate'],'geometry_errors':len(errors),'ignored_hidden_members':ignored,'validation':{'all_passed':True,'row_count':True,'unique_ids_no_missing':True,'status_totals':True,'area_references':True,'nonmatched_area_empty':True,'area_totals':True,'id_source_external_exact_csv_roundtrip':True,'review_count_and_unique_ids':True,'manifest_hashes_counts':True},'boundary_version':'project-preview-20261103','effective_on':None,'verified':False,'reference_on':'2026-11-03','crs':'Assume same longitude/latitude CRS; no authoritative EPSG or transform history verified','libraries':{'python':platform.python_version(),'shapely':shapely.__version__,'GEOS':shapely.geos_version_string},'identity_sha256':input_digest.hexdigest()}
 dump(out/'store_area_summary.json',summary)
 notes=f'''# 서울 매장 ↔ 상권 미리보기 대응표

전체 {total:,}건, 상권 {len(ids):,}개. 원본 변경 없음. DB 적재/서비스 수정 없음.

## 입력 구조와 ID
ZIP manifest.process_order의 PublicStore 분할 JSON 56개를 사용. 배열의 model/fields 구조이며 public_store_id=fields.id, source_id=fields.source_id, external_id=fields.external_id. area_id=CommercialArea.fields.id (code가 아님). 원본 ID를 새로 발급하지 않음. JSON 숫자 ID는 CSV 십진 문자열로 출력하고 문자열 ID와 external_id는 그대로 보존. CSV는 UTF-8 BOM. Excel에서 열 때 ID 열을 텍스트로 가져와야 함.
매장 longitude/latitude 원본 문자열은 수정하지 않고 계산 때만 Python float(IEEE 754 binary64)로 변환. 경계는 GeoJSON [longitude, latitude].

## 좌표계 근거와 가정
DataSource.note는 원본 경도·위도 사용 및 좌표계 변환 이력 미확인이라고 명시. 경계에는 authoritative CRS/EPSG 선언 없음. 경위도 필드명/GeoJSON 구조는 축 순서 근거이나 동일 datum을 증명하지 못함. 두 자료가 동일 경위도 좌표계라고 가정하여 평면 XY 위상 판정 수행. EPSG:4326 공식 확인이나 CRS 변환은 하지 않음. 범위만으로 좌표계 확정하지 않음.
경계 version=project-preview-20261103, effective_on=null, verified=false. 공식 기준일/변환 이력 미확정. 매장 reference_on=2026-11-03은 프로젝트 스냅샷 날짜.

## 알고리즘
모든 Polygon/MultiPolygon, 내부 구멍 및 구멍 경계 반영. 폐합·좌표·유효성 검증 후 STRtree의 축 정렬 bounding box 후보 전체에 g.touches(point)와 g.contains(point)를 적용. bbox 밖 도형은 점과 만날 수 없어 생략 가능. 하나라도 touches면 boundary, 그렇지 않고 contains 두 개 이상이면 overlap, 하나면 matched, 없으면 outside. 잘못된 좌표는 invalid_coordinate. geometry 오류 시 진단 저장 후 assert로 중단하며 임의 복구/제외하지 않음.
review.reason은 interior_area_ids와 boundary_area_ids를 별도 보관. candidate_area_ids는 두 배열의 합집합 JSON. matched만 area_id 기입.

## 경계선 및 수치
정확한 사용 함수: shapely geometry.touches(Point), geometry.contains(Point), STRtree.query(Point). 임의 epsilon/거리 허용오차 없음(0), 버퍼/반올림/보정/최근접 없음. GEOS 부동소수점 위상 판정이며 임의정밀 산술 또는 측량 정확도 보장은 아님. 경계에 매우 가까워도 touches가 False면 boundary로 확대하지 않음.

## 실행과 검증
Python {platform.python_version()}, Shapely {shapely.__version__}, GEOS {shapely.geos_version_string}. requirements.txt 참조. 원본 ZIP을 풀어 편집하지 않고 ZipFile에서 읽음. 점으로 시작하는 경로 구성요소는 manifest에 있더라도 제외. 입력 manifest의 비숨김 파일 해시 및 JSON 건수 모두 검증. ZIP 컨테이너/상권 JSON SHA도 산출 manifest에 기록.

```bash
python -m pip install -r requirements.txt
python process_store_area.py --stores-zip seoul_public_stores_20261103.zip --areas 02_areas.json --output result
```
출력은 새 디렉터리로 지정. 실패 시 기존 출력물은 최종 결과로 사용하지 말 것.
필수 검증: 입력/CSV 건수, ID 중복/누락, ID·source_id·external_id 순서 포함 전체 SHA 대조, 상태 합계, matched 실제 ID 존재, 비matched 빈 area_id, 상권별 합계, review 건수 및 유일성 통과. 검증 상세는 summary.validation.

## 한계
공식 검증이 아닌 프로젝트 미리보기. 1,643개 입력 경계 전체에 대한 계산 완전성만 확인하며, 실제 누락 상권·원본 정확도·최신성은 증명하지 않음. outside는 영업 여부나 주소 오류를 의미하지 않음. 서로 다른 상권 유형도 모두 비교하여 중첩은 그대로 overlap 처리. 브랜드/상호명/주소 추정 연결 없음.
공식 함수 설명: https://shapely.readthedocs.io/en/stable/strtree.html 및 https://shapely.readthedocs.io/en/stable/manual.html
'''
 (out/'store_area_mapping_notes.md').write_text(notes,encoding='utf-8')
 (out/'requirements.txt').write_text(f'shapely=={shapely.__version__}\nnumpy=={__import__("numpy").__version__}\n',encoding='utf-8')
 script=Path(__file__).resolve()
 if script!= (out/script.name).resolve():shutil.copyfile(script,out/script.name)
 outputs=[]
 rowcounts={'store_area_mapping.csv':total,'store_area_review.csv':total-counts['matched'],'geometry_validation.json':len(areas),'store_area_summary.json':1}
 for f in sorted(out.iterdir()):
  if f.is_file() and f.name!='manifest.json':outputs.append({'filename':f.name,'records':rowcounts.get(f.name),'sha256':sha(f.read_bytes())})
 dump(out/'manifest.json',{'inputs':inputs,'input_archive':{'filename':Path(args.stores_zip).name,'sha256':sha(Path(args.stores_zip).read_bytes())},'outputs':outputs,'records_null_means':'not a record table','ignored_hidden_members':ignored})
 print(json.dumps(counts),flush=True)
if __name__=='__main__':main()
