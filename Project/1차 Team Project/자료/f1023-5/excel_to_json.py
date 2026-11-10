"""프차탄탄 업종별 엑셀 4개 -> 원본 전체 구조를 보존한 JSON 생성 (DB 변경 없음).
사용: python -m pip install openpyxl
      python excel_to_json.py --source priority_brands.json
      python excel_to_json.py --source priority_brands.json --apply-json
기본은 검증/미리보기만. --apply-json 시 output/priority_brands_updated.json 생성.
"""
import argparse,copy,json,pathlib,sys,datetime
from collections import Counter
try:
 from openpyxl import load_workbook
except ImportError:
 sys.exit('openpyxl 필요: python -m pip install openpyxl')
BASE=pathlib.Path(__file__).resolve().parent
CATEGORIES=('카페','치킨','편의점','미용실')
SHEETS={'브랜드기본':('id',),'연도별통계':('brand_id','year'),'지역별통계':('brand_id','year','region'),'전국참고':('brand_id','year'),'창업비용':('brand_id','year')}
NULL_MARKER='__NULL__'

def norm(value, old):
 if value is None or value=='':
  return old if old is not None else None
 if isinstance(value,str) and value.strip()==NULL_MARKER:
  return None
 if isinstance(old,bool):
  if value in (True,False):return value
  if isinstance(value,str) and value.lower() in ('true','false'):return value.lower()=='true'
  raise ValueError('불리언은 TRUE/FALSE만 입력')
 if isinstance(value,datetime.datetime):raise ValueError('날짜 형식 입력 불가')
 if isinstance(value,float) and value.is_integer():value=int(value)
 if isinstance(old,int) and not isinstance(old,bool):
  if isinstance(value,bool):raise ValueError('숫자 대신 불리언 입력')
  if isinstance(value,str):
   if not value.strip().lstrip('-').isdigit():raise ValueError('정수 필요')
   value=int(value.strip())
  if not isinstance(value,int):raise ValueError('정수 필요')
 if old is None and isinstance(value,str):
  v=value.strip()
  if v.lstrip('-').isdigit():return int(v)
  if v.lower() in ('true','false'):return v.lower()=='true'
 return value

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--source',default=str(BASE/'data'/'priority_brands.json'))
 ap.add_argument('--apply-json',action='store_true',help='검증 통과 시 JSON 결과 파일 생성 (DB 변경 없음)')
 args=ap.parse_args()
 source=pathlib.Path(args.source).resolve()
 if not source.is_file():sys.exit(f'원본 파일이 없습니다: {source}')
 data=json.loads(source.read_text(encoding='utf-8'))
 if not isinstance(data,list):sys.exit('원본은 브랜드 객체 리스트여야 합니다')
 schema=json.loads((BASE/'schema.json').read_text(encoding='utf-8'))
 idx={b['id']:b for b in data};errors=[];changes=[];seen=set();expected=set()
 for cat in CATEGORIES:
  expected|={b['id'] for b in data if b['category']==cat and b['id'] in TARGET_IDS}
  xlsx=BASE/'data'/'excel'/f'{cat}.xlsx'
  if not xlsx.is_file():errors.append(f'파일 누락: {xlsx}');continue
  wb=load_workbook(xlsx,data_only=True,read_only=True)
  for sheet_name,keys in SHEETS.items():
   if sheet_name not in wb.sheetnames:errors.append(f'{cat}: 시트 누락 {sheet_name}');continue
   ws=wb[sheet_name];iterator=ws.iter_rows(values_only=True)
   try:headers=next(iterator)
   except StopIteration:errors.append(f'{cat}/{sheet_name}: 빈 시트');continue
   headers=[str(v) if v is not None else '' for v in headers]
   expected_headers={'브랜드기본':schema['brand_fields'],'연도별통계':['brand_id']+schema['annual_fields'],'지역별통계':['brand_id','year','region']+schema['region_fields'],'전국참고':['brand_id','year']+schema['national_fields'],'창업비용':['brand_id','year']+schema['cost_fields']}[sheet_name]
   if headers!=expected_headers:
    errors.append(f'{cat}/{sheet_name}: 헤더가 변경되었습니다');continue
   sheet_seen=set()
   for rowno,row in enumerate(iterator,2):
    if all(v is None for v in row):continue
    rec=dict(zip(headers,row));key=tuple(rec.get(k) for k in keys)
    if key in sheet_seen:errors.append(f'{cat}/{sheet_name} {rowno}행: 중복 키 {key}');continue
    sheet_seen.add(key)
    brand_id=rec.get('id') if sheet_name=='브랜드기본' else rec.get('brand_id')
    if brand_id not in TARGET_IDS or brand_id not in idx or idx[brand_id]['category']!=cat:
     errors.append(f'{cat}/{sheet_name} {rowno}행: 허용되지 않은 브랜드 ID {brand_id}');continue
    brand=idx[brand_id]
    if sheet_name=='브랜드기본':target=brand
    else:
     year=rec.get('year')
     target=next((h for h in brand['history'] if h['year']==year),None)
     if target is None:errors.append(f'{cat}/{sheet_name} {rowno}행: 원본에 없는 연도 {year}');continue
     if sheet_name=='지역별통계':
      region=rec.get('region');target=target.get('regions',{}).get(region)
      if target is None:errors.append(f'{cat}/{sheet_name} {rowno}행: 원본에 없는 지역 {region}');continue
     elif sheet_name=='전국참고':target=target.get('national_reference')
     elif sheet_name=='창업비용':target=target.get('startup_cost_breakdown')
     if target is None:errors.append(f'{cat}/{sheet_name} {rowno}행: 원본 하위 데이터 없음');continue
    for field,value in rec.items():
     if field in keys:continue
     if field not in target:
      errors.append(f'{cat}/{sheet_name} {rowno}행: 원본에 없는 필드 {field}');continue
     old=target[field]
     try:new=norm(value,old)
     except (ValueError,TypeError) as e:
      errors.append(f'{cat}/{sheet_name} {rowno}행 {field}: {e}');continue
     if new!=old:
      # 원본 JSON 내 정수/불리언/문자열 필드 타입 보존
      if old is None and new is not None and isinstance(new,float) and new.is_integer():new=int(new)
      if old is not None and new is not None and type(old)!=type(new):
       errors.append(f'{cat}/{sheet_name} {rowno}행 {field}: 데이터 타입 불일치 {type(old).__name__}->{type(new).__name__}');continue
      changes.append({'업종':cat,'시트':sheet_name,'브랜드ID':brand_id,'연도':rec.get('year'),'지역':rec.get('region'),'필드':field,'기존값':old,'수정값':new})
      target[field]=new
   # Missing row protection: no partial workbook import
   if sheet_name=='브랜드기본':required={(b['id'],) for b in data if b['id'] in TARGET_IDS and b['category']==cat}
   elif sheet_name in ('연도별통계','전국참고','창업비용'):
    required={(b['id'],h['year']) for b in data if b['id'] in TARGET_IDS and b['category']==cat for h in b['history']}
   else:required={(b['id'],h['year'],region) for b in data if b['id'] in TARGET_IDS and b['category']==cat for h in b['history'] for region in h.get('regions',{})}
   if sheet_seen!=required:errors.append(f'{cat}/{sheet_name}: 행 누락/추가. 누락 {len(required-sheet_seen)}개, 추가 {len(sheet_seen-required)}개')
  wb.close()
 outdir=BASE/'output';outdir.mkdir(exist_ok=True)
 report={'source':str(source),'brand_count':len(data),'target_brands':len(TARGET_IDS),'change_count':len(changes),'error_count':len(errors),'errors':errors,'changes':changes}
 (outdir/'변경검토.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'검증: 전체 {len(data)}개 / 대상 {len(TARGET_IDS)}개 / 변경 {len(changes)}건 / 오류 {len(errors)}건')
 for e in errors[:25]:print('오류:',e)
 for c in changes[:15]:print('변경:',c['브랜드ID'],c['시트'],c['필드'],repr(c['기존값']),'→',repr(c['수정값']))
 print('변경 보고서:',outdir/'변경검토.json')
 if errors:sys.exit('오류가 있어 JSON을 생성하지 않았습니다.')
 if args.apply_json:
  dest=outdir/'priority_brands_updated.json'
  if dest.resolve()==source:sys.exit('원본 덮어쓰기 금지')
  dest.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  print('JSON 생성:',dest)
 else:print('미리보기 모드: JSON은 생성하지 않았습니다. 생성하려면 --apply-json 추가')

if __name__=='__main__':
 # 고정된 대상 19개 브랜드. 스키마 내 ID 목록을 신뢰하며 다른 브랜드는 변경하지 않음
 TARGET_IDS=set(json.loads((BASE/'target_ids.json').read_text(encoding='utf-8')))
 main()
