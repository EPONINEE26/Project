"""Python 3 standard library only. Run: python process_public_stores.py INPUT.csv OUTPUT_DIR
Output directory must be empty. Input is never modified. Data record numbering starts at 2 (header=1).
"""
import csv,json,hashlib,sqlite3,tempfile,sys,re,shutil
from pathlib import Path
from decimal import Decimal,InvalidOperation
from collections import defaultdict,Counter

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
def main(inp,out):
 inp=Path(inp);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 if list(out.iterdir()):raise ValueError('Output directory must be empty')
 tmp=tempfile.TemporaryDirectory();db=sqlite3.connect(str(Path(tmp.name)/'stage.db'))
 db.execute('create table rows(n integer, ext text, raw text)');names=defaultdict(set);total=0
 with inp.open(encoding='cp949',newline='') as f:
  r=csv.DictReader(f);cols=r.fieldnames
  if len(set(cols))!=len(cols):raise ValueError('Duplicate headers')
  for n,row in enumerate(r,2):
   if None in row or any(v is None for v in row.values()):raise ValueError(f'Malformed CSV record {n}')
   total+=1;names[row['상권업종소분류코드']].add(row['상권업종소분류명'])
   db.execute('insert into rows values(?,?,?)',(n,row['상가업소번호'],json.dumps(row,ensure_ascii=False)))
 db.commit();db.execute('create index ext_idx on rows(ext)')
 db.execute('create table groups as select ext,count(*) ct,count(distinct raw) variants,min(n) first_n from rows group by ext');db.execute('create unique index group_idx on groups(ext)')
 reports={};writers={}
 for name,extra in [('rejected_rows',['reasons']),('industry_conflicts',['issue']),('postcode_issues',['issue','normalized_postcode']),('coordinate_outliers',['issue']),('non_seoul_rows',['issue']),('duplicate_rows',['kept_row_number'])]:
  f=(out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='');reports[name]=f;w=csv.writer(f);w.writerow(['original_row_number']+extra+cols);writers[name]=w
 def report(kind,n,row,*extra):writers[kind].writerow([n,*extra,*[row[k] for k in cols]])
 valid={c:next(iter(ns)) for c,ns in names.items() if c.strip() and len(c)<=30 and len(ns)==1 and next(iter(ns)).strip() and len(next(iter(ns)))<=100}
 ids={c:i for i,c in enumerate(sorted(valid),1)}
 dump(out/'03_industry_codes.json',[{'model':'IndustryCode','fields':{'id':ids[c],'system':'local-sbiz-small-20261103','code':c,'name':valid[c],'brand_category':'','verified':False}} for c in sorted(ids)])
 note='프로젝트 자료 취합일을 수집일로 사용.\n원본 seoul_store.csv.\n원본 통계 기준일은 미확인.\n매장 reference_on은 공식 영업 기준일이 아닌 프로젝트 스냅샷 날짜.\n좌표는 원본 경도·위도 값을 사용하며 좌표계 변환 이력은 미확인.'
 dump(out/'10_public_store_source.json',[{'model':'DataSource','fields':{'id':3,'name':'서울 상가정보 CSV (프로젝트 취합본)','url':'','collected_on':'2026-11-03','note':note}}])
 stats=Counter();reasons_count=Counter();districts=Counter();industries=Counter();batch=[];files=[];previous=None
 for n,ext,raw,ct,variants,first in db.execute('select r.n,r.ext,r.raw,g.ct,g.variants,g.first_n from rows r join groups g on r.ext=g.ext order by r.ext collate binary,r.n'):
  row=json.loads(raw);reasons=[];c=row['상권업종소분류코드'];nm=row['상권업종소분류명']
  if c not in ids:
   issue='missing_code_or_name' if not c.strip() or not nm.strip() else ('conflicting_names' if len(names[c])>1 else 'industry_length_exceeded')
   report('industry_conflicts',n,row,issue);stats['industry_issue_rows']+=1
  pc=row['신우편번호'];postcode=pc.zfill(5) if re.fullmatch(r'[0-9]{1,5}',pc) else ''
  if pc and not postcode:report('postcode_issues',n,row,'invalid_postcode','');stats['postcode_invalid']+=1
  elif pc and pc!=postcode:stats['postcode_padded']+=1
  elif not pc:stats['postcode_missing']+=1
  coords=[]
  for key,limit in [('위도',90),('경도',180)]:
   try:
    if not row[key].strip():raise ValueError('missing')
    v=Decimal(row[key])
    if not v.is_finite():raise ValueError('nonfinite')
    if not -limit<=v<=limit:raise ValueError('range')
    digits_tuple,exp=v.as_tuple()[1:];digits=len(digits_tuple)
    if exp>=0:
     if digits_tuple!=(0,):digits+=exp
     decimals=0
    else:decimals=abs(exp);digits=max(digits,decimals)
    if digits>30 or decimals>25 or digits-decimals>5:raise ValueError('precision')
    coords.append(v)
   except (InvalidOperation,ValueError) as e:reasons.append(key+':'+str(e));coords.append(None)
  if all(v is not None for v in coords) and not (Decimal('37.3')<=coords[0]<=Decimal('37.8') and Decimal('126.7')<=coords[1]<=Decimal('127.3')):
   report('coordinate_outliers',n,row,'outside_screening_box_126.7_127.3_37.3_37.8');stats['coordinate_outliers']+=1
  if row['시도명']!='서울특별시' or row['시도코드']!='11':
   reasons.append('non_seoul_or_missing_province');report('non_seoul_rows',n,row,'province_name_or_code_not_seoul');stats['non_seoul']+=1
  name=row['상호명'];branch=row['지점명']
  if branch.strip() and branch not in name:name=name+' '+branch
  address=row['도로명주소'] if row['도로명주소'].strip() else row['지번주소']
  if not row['상호명'].strip():reasons.append('missing_name')
  if len(name)>200:reasons.append('name_length_exceeded')
  if not address.strip():reasons.append('missing_address')
  if len(address)>300:reasons.append('address_length_exceeded')
  if not ext.strip():reasons.append('missing_external_id')
  if len(ext)>100:reasons.append('external_id_length_exceeded')
  if variants>1 and ext.strip():reasons.append('external_id_conflict')
  # Rejected takes precedence over exact duplicate accounting; every input row has one outcome.
  if reasons:
   stats['rejected']+=1;reasons_count.update(set(reasons));report('rejected_rows',n,row,';'.join(reasons));continue
  if n!=first:
   stats['duplicates_removed']+=1;report('duplicate_rows',n,row,first);continue
  assert previous is None or previous<ext
  previous=ext;stats['output']+=1;i=stats['output'];districts[row['시군구명']]+=1;industries[c if c in ids else '(null)']+=1
  fields=dict(id=i,source_id=3,external_id=ext,name=name,industry_id=ids.get(c),brand_id=None,area_id=None,address=address,postcode=postcode,latitude=row['위도'],longitude=row['경도'],reference_on='2026-11-03',raw=row)
  batch.append({'model':'PublicStore','fields':fields})
  if len(batch)==10000:
   fn=f'07_public_stores_{len(files)+1:04d}.json';dump(out/fn,batch);files.append((fn,len(batch)));batch=[]
 if batch:
  fn=f'07_public_stores_{len(files)+1:04d}.json';dump(out/fn,batch);files.append((fn,len(batch)))
 for f in reports.values():f.close()
 assert total==stats['output']+stats['rejected']+stats['duplicates_removed']
 # Re-read every JSON, verify format, all IDs, relationships, ordering and raw string values.
 count=0;prev=None
 for fn,size in files:
  data=json.loads((out/fn).read_text(encoding='utf-8'));assert len(data)==size<=10000
  for rec in data:
   f=rec['fields'];count+=1;assert f['id']==count and (prev is None or prev<f['external_id']);prev=f['external_id']
   assert f['industry_id'] is None or f['industry_id'] in ids.values()
   assert f['source_id']==3 and f['brand_id'] is None and f['area_id'] is None
   assert all(isinstance(v,str) for v in f['raw'].values())
   assert f['latitude']==f['raw']['위도'] and f['longitude']==f['raw']['경도']
 assert count==stats['output']
 shutil.copyfile(__file__,out/'process_public_stores.py')
 report_text=f'''# 공공 매장 CSV 가공 검증 보고서

입력: {inp.name} (CP949), 전체 {total:,}행. CSV 헤더 제외 논리 레코드 번호 + 1을 원본 행 번호로 사용합니다. 여러 줄 값은 한 레코드입니다.
출력 {stats['output']:,}건 + 제외 {stats['rejected']:,}행 + 동일 중복 제거 {stats['duplicates_removed']:,}행 = {total:,}행. 검산 통과.
매장 파일 {len(files)}개, 업종 {len(ids)}개. ID 연속성·external_id 파일 간 중복·문자열 정렬·업종 FK·raw 문자열·좌표 원문 일치 재검사 통과.

## 필드 대응표

| 모델 필드 | 원본/규칙 |
|---|---|
| external_id | 상가업소번호, 원문 문자열 |
| name | 상호명 + 지점명(이미 포함된 경우 추가하지 않음) |
| address | 도로명주소 우선, 공백/누락 시 지번주소 |
| postcode | 신우편번호, ASCII 숫자 1~5자리만 5자리 0 채움 |
| latitude / longitude | 위도 / 경도 원문 숫자 문자열 |
| industry_id | 소분류코드 오름차순 ID, 충돌/누락은 null |
| source_id / brand_id / area_id | 3 / null / null |
| reference_on | 2026-11-03 프로젝트 스냅샷 |
| raw | 모든 {len(cols)}열의 문자열 그대로 |

## 검사 및 처리 규칙

동일 식별자의 내용 충돌은 해당 식별자 모든 행 제외. 완전히 같은 행은 최초 행만 사용. 제외 사유가 있는 행은 제외에만 집계하며 중복 제거와 중복 계산하지 않습니다. duplicate_rows.csv는 실제 제거한 동일 중복입니다.
업종 코드는 전체 입력을 기준으로 이름 충돌, 누락 및 길이를 검사합니다. industry_conflicts.csv에는 해당 원본 행을 모두 기록하며, 정상 코드에 이름 누락이 섞인 경우도 충돌로 처리합니다.
정리된 필드는 공백을 임의 제거하지 않으며 공백뿐인 값은 누락으로 판정합니다. 원본 raw는 수정하지 않습니다. 과학적 표기의 원래 정수 복원은 하지 않았습니다.
좌표는 Decimal 유한값·위도 ±90·경도 ±180·전체 30자리·소수 25자리·정수 5자리 제한을 검사했습니다. 좌표 반올림·변환·교환은 하지 않았습니다.
서울 주변 이상치 선별 상자: 경도 126.7~127.3, 위도 37.3~37.8 (경계 포함). 상자 밖은 보고하되 유효 좌표는 보존합니다. 서울 행정경계 소속 검증이 아닙니다. 시도명 서울특별시 및 코드 11 모두 만족해야 출력합니다.
필수값 및 최대 길이: external_id 100, name 200, address 300; 업종 system 50/code 30/name 100/brand_category 30. 임의 절단 없음.

검사 집계(우편번호·이상치는 전체 입력 기준, 제외와 중복될 수 있음):

```json
{json.dumps(dict(stats),ensure_ascii=False,indent=2)}
```
제외 사유별 행 수(복수 사유 중복 가능):

```json
{json.dumps(dict(reasons_count),ensure_ascii=False,indent=2)}
```

## 출력 업종별 건수

| 코드 | 업종명 | 건수 |
|---|---|---:|
'''
 for c in sorted(industries):report_text+=f'| {c} | {valid.get(c,"미결정")} | {industries[c]} |\n'
 report_text+='\n## 출력 자치구별 건수\n\n| 자치구 | 건수 |\n|---|---:|\n'
 for c,v in sorted(districts.items()):report_text+=f'| {c} | {v} |\n'
 report_text+='''
## 처리 및 가져오기 순서

10_public_store_source.json → 03_industry_codes.json → 07_public_stores_0001.json부터 파일명 순서.
첨부 import_analysis는 검증 모드에서도 개별 파일 내 저장 후 트랜잭션을 롤백합니다. 따라서 출처와 업종이 DB에 없으면 매장 파일 단독 검증은 FK 오류가 납니다. 실제 적재 시 출처·업종을 먼저 --commit으로 저장해야 다음 파일에서 참조할 수 있습니다.

기존 IndustryCode/PublicStore ID와 충돌하면 이 명령은 해당 ID를 갱신할 수 있습니다. 제공된 DB가 없어 기존 ID 점유 여부는 확인하지 않았습니다. 기존 ID와 충돌 여부를 로컬 DB에서 먼저 확인해야 합니다. DataSource 1,2는 결과에 포함하지 않습니다.

Windows PowerShell 재실행(빈 출력 폴더 사용):

```powershell
python .\\process_public_stores.py '.\\seoul_store.csv' '.\\public_store_output'
```

## 미확인 정보 및 검증 한계

직접 원문 URL, 공식 통계 기준일, 공식 업종 버전, 좌표계와 변환 이력, 실제 영업 상태는 미확인입니다. 업종 system은 프로젝트 내부 식별자입니다. collected_on 및 reference_on은 2026-11-03 프로젝트 취합/스냅샷 날짜입니다.
첨부 소스 구조와 필드 제한에 대한 파일 검증이며 Django import_analysis 실행·DB 적재·지도 API 연결은 수행하지 않았습니다.
Decimal 검증 규칙 참고: https://docs.djangoproject.com/en/6.1/ref/validators/#decimalvalidator
'''
 (out/'validation_report.md').write_text(report_text,encoding='utf-8')
 counts=dict(files);counts.update({'03_industry_codes.json':len(ids),'10_public_store_source.json':1})
 for p in out.glob('*.csv'):
  with p.open(encoding='utf-8-sig',newline='') as f:counts[p.name]=sum(1 for _ in csv.reader(f))-1
 manifest={'original_filename':inp.name,'original_sha256':sha(inp),'input_rows':total,'output_stores':stats['output'],'excluded_rows':stats['rejected'],'identical_duplicates_removed':stats['duplicates_removed'],'industry_count':len(ids),'counts_reconcile':True,'source_id':3,'process_order':['10_public_store_source.json','03_industry_codes.json']+[f for f,n in files],'files':[{'filename':p.name,'records':counts.get(p.name),'sha256':sha(p)} for p in sorted(out.iterdir())],'manifest_hash_note':'manifest itself is excluded to avoid circular hash','validation':'all output JSON re-read; continuous IDs, unique sorted external IDs, FK references and raw coordinate strings checked','input_encoding':'cp949','output_encoding':'UTF-8 (CSV reports UTF-8 BOM)','coordinate_screening_box':{'longitude':[126.7,127.3],'latitude':[37.3,37.8]}}
 dump(out/'manifest.json',manifest);print(json.dumps(manifest,ensure_ascii=False)[:500],flush=True)
 db.close();tmp.cleanup()
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
