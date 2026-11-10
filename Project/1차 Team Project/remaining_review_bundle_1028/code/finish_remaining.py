import json,csv,pathlib,collections,zipfile,shutil,ast,math
D=pathlib.Path('remaining_output');S=json.load(open(D/'summary.json'));sourceids=collections.defaultdict(set)
for r in csv.DictReader(open(D/'match_audit.csv',encoding='utf-8-sig')):
 if r['status']=='map':sourceids[r['source']].add(r['bizesId'])
B={};allids=set();coordinates=0
for p in (D/'maps').glob('*.json'):
 B[p.stem]=json.load(open(p))
 for b in B[p.stem]:
  for region,ms in b['regions'].items():
   for m in ms:
    assert m['bizesId'] not in allids;allids.add(m['bizesId']);assert type(m['lat']) in [int,float] and math.isfinite(m['lat']) and type(m['lon']) in [int,float] and math.isfinite(m['lon']);coordinates+=1
assert coordinates==S['map_rows']
# Category label comes from archive filename; source's display-category labels may contain spaces.
code=ast.parse(pathlib.Path('process_remaining.py').read_text());node=next(n for n in code.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='allowed' for t in n.targets));allowed={ast.literal_eval(k):set(ast.literal_eval(v.args[0])) for k,v in zip(node.value.keys,node.value.values)}
(D/'maps_by_source').mkdir(exist_ok=True)
for sector,cats in allowed.items():
 data=[]
 for cat in B:
  if cat not in cats:continue
  for b in B[cat]:data.append({'id':b['id'],'name':b['name'],'regions':{r:[m for m in ms if m['bizesId'] in sourceids[sector]] for r,ms in b['regions'].items()}})
 assert sum(len(ms) for b in data for ms in b['regions'].values())==S['sources'][sector]['counts']['map']
 (D/'maps_by_source'/(sector+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
S['validation'].update({'map_unique_bizesId':'PASS','map_coordinates_numeric_finite':'PASS','five_source_map_totals':'PASS'})
# Search evidence is review scope, never a claim that all shops have been verified.
E=[{'topic':'CU·GS25·GS더프레시·이마트24 별칭/공식 안내','links':['https://cu.bgfretail.com/','https://cs.bgfretail.com/','https://gs25.gsretail.com/gscvs/ko/main','https://gs25.gsretail.com/gscvs/ko/membership-services/gs-retail','https://m.emart24.co.kr/store'],'finding':'공식 브랜드 표기와 안내 경로 확인. 브랜드별칭 점검이며 개별 점포 전수 검증은 아님.'},
{'topic':'깊은생각 같은 주소 다층 후보','links':['https://play.google.com/store/apps/details?id=com.dailystudy.dailystudy2','https://www.gangmom.kr/institute/65b7af56b8368381372efea4','https://bizsurfing.com/p/424953/깊은생각필연의길1관보습학원'],'records':[3037,3714,67847,77113],'source':'교육서비스업','finding':'공식 앱 개발자 주소는 도곡로457 5층. 공개 학원 안내에 같은 주소의 1층 상담센터와 3층 학원도 나타남. 복수 층을 사용하는 같은 학원인지 별도 등록 단위인지 확정 불가. 전부 보류, 삭제/병합 없음.'},
{'topic':'에듀코치 신갈 동일명/주소','links':['https://www.localview.co.kr/store/detail.asp?seq=102469307','https://edu-coach.kr/'],'records':[567,76592],'source':'교육서비스업','finding':'공개 에듀코치 안내와 이름이 같은 별도 교육 컨설팅 사이트도 검색됨. 신갈의 두 CSV행 관계를 공식 자료로 확인하지 못함. 브랜드 이름 검색 결과만으로 동일 사업체라 단정하지 않고 보류.'},
{'topic':'튼튼영어 평화','links':['https://place.udanax.org/p/1435070/찬스실용음악학원'],'records':[3166,44088],'source':'교육서비스업','finding':'공개 장소의 인근 업체 안내에 소대배기로18 3층 평화어학원 표기. 두 CSV 상가ID가 하나인지 여부는 확인 불가. 모두 보류.'},
{'topic':'크린토피아·리챠드프로헤어 공식 확인 경로','links':['https://www.cleantopia.com/kr/useInfo/cleanApp.do','https://leechstyle.com/index.php','https://leechstyle.com/bbs/store.php?idx=10'],'finding':'공식 매장정보/위치 확인 경로를 확인. 리챠드 단독 등 약칭을 이 근거만으로 일괄 승격하지 않음.'},
{'topic':'숙박·교육의 공개 확인 경로','links':['https://access.visitkorea.or.kr/acm/detail.do?cotId=ac103fba-0b83-473c-b595-7c2266150df5','https://cdto.creverse.com/cdi/dongdaemun/cs/faq/list'],'finding':'한국관광공사 넘버25호텔 사례와 청담어학원 공식 브랜치 페이지 확인. 전체 매장의 현재 영업이나 브랜드 연결 검증 아님.'}]
(D/'search_evidence.json').write_text(json.dumps(E,ensure_ascii=False,indent=2))
dups=json.load(open(D/'duplicate_review.json'))
for d in dups:
 es=[e for e in E if any(r['source']==e.get('source') and r['csv_record'] in e.get('records',[]) for r in d['rows'])]
 if es:d['source_links']=list(dict.fromkeys(u for e in es for u in e['links']));d['search_notes']=[e['finding'] for e in es]
 d['search_status']='reviewed_unresolved' if es else 'not_individually_web_searched'
(D/'duplicate_review.json').write_text(json.dumps(dups,ensure_ascii=False,indent=2))
(D/'summary.json').write_text(json.dumps(S,ensure_ascii=False,indent=2))
with open(D/'region_audit.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['source','region','source_rows','map_rows','pending_rows','no_candidate_rows']);ct=collections.Counter()
 for r in csv.DictReader(open(D/'row_disposition.csv',encoding='utf-8-sig')):ct[r['source'],r['ctprvnNm'],r['status']]+=1
 for source,ss in S['sources'].items():
  for region,total in ss['source_regions'].items():
   ns=[ct[source,region,k] for k in ['map','pending','no_candidate']];assert sum(ns)==total;w.writerow([source,region,total,*ns])
L=['# 나머지 5개 업종 프랜차이즈 지도 데이터 검토 보고서','','처리일: 2026-10-28. 새로 첨부한 5개 업종 ZIP 내부 records.csv와 brands_by_category(1).zip을 사용했습니다. ZIP의 records.json은 CSV와 중복 입력하지 않았습니다.','','## 범위와 결과','','**이번 파일은 새로 첨부한 5개 업종 자료만의 처리 결과입니다. 이전 음식업 CSV·카페 결과를 합치거나 대체한 완성 전국 통합본이 아닙니다.** 브랜드 기준의 45개 카테고리·12,498개 브랜드를 보존한 maps/와, 이번 5개 원본 업종별 maps_by_source/를 제공합니다. 카테고리 파일은 id/name/regions 형태의 브랜드 배열입니다. 업종별 파일은 사전에 대응한 관련 카테고리 브랜드를 빈 배열까지 포함하며, 해당 CSV에서 채택한 매장만 담습니다. 브랜드는 기준에 없는 것을 추가하지 않았습니다.','','| 원본 업종 | 전체 행 | 지도 채택 | 판단 보류 | 후보 미검출 |','|---|---:|---:|---:|---:|']
for sec,ss in S['sources'].items():
 c=ss['counts'];L.append(f"| {sec} | {c['source_rows']:,} | {c.get('map',0):,} | {c.get('pending',0):,} | {c['no_candidate']:,} |")
no=S['source_rows']-S['map_rows']-S['pending_rows'];L += [f"| 합계 | {S['source_rows']:,} | {S['map_rows']:,} | {S['pending_rows']:,} | {no:,} |",'',f"매장 행이 있는 브랜드 {S['brands_with_map_rows']:,}개. 보류 중 연결 근거가 있는 후보 {S['pending_with_link_basis']:,}행, 나머지 {S['pending_rows']-S['pending_with_link_basis']:,}행은 부분포함·과거명·미검증 약칭 등 넓은 탐색입니다. 미검출은 해당 브랜드가 아니라고 확인한 수가 아니며, 약한 문자열 후보에는 무관 업소도 포함됩니다.",'','## 매칭과 지역 처리','','공백·기호·대소문자·HTML 엔티티·악센트를 정규화했습니다. 한영 병기 괄호 안팎, 입력의 history/name_variants, 제한된 업태어 제거 약칭을 대조합니다. 전체 상호 또는 이름 접두부 뒤에 지점/학원/교습소 표기나 원본 주소·동·지점 단서가 있는 경우만 연결 후보로 삼습니다. 중간에 이름이 일부 들어간 것만으로 지도에 넣지 않습니다. 과거명과 자동 생성 약칭은 검토 후보로만 남깁니다. 동일 별칭의 복수 ID는 임의 선택하지 않습니다. 짧은 이름·일반명·복합상호·시설 가능성은 보류합니다. 명시적 예외와 업종-카테고리 대응표는 code/process_remaining.py에 있습니다. 대응표는 법적 업종 판정이 아닌 보수적 선별 규칙입니다. 업종이 다르다는 이유로 원본을 버리지 않고 cross_sector_review로 남깁니다.','','브랜드 파일 내부 category 표시명과 파일명의 공백/밑줄 차이는 카테고리 파일명을 기준으로 일관되게 대응했습니다. id와 name은 변경하지 않았습니다. 입력 name=null도 임의 이름을 만들지 않고 유지합니다. history 매출·매장 수 통계는 위치 정보로 사용하지 않았습니다.','','지역 키는 서울·부산·대구·인천·광주·대전·울산·세종·경기·강원·충북·충남·전북·전남·경북·경남·제주 및 전남광주통합특별시입니다. 특별시/광역시/도 이름을 기준의 약칭으로만 대응합니다. 전남광주통합특별시는 원본 그대로 별도 키에 두며 광주·전남으로 분할하지 않습니다. 광주/전남의 빈 배열은 매장이 없다는 확인이 아닙니다. 해당 원본 값은 현재 행정구역이라는 법적 판단 없이 보존했습니다.','','## 매장 필드','','rdnmAdr, bldNm, lat, lon, bizesId, bizesNm, brchNm, ctprvnNm, signguNm, dongNo, flrNo, hoNo, marker_title을 담았습니다. 좌표는 숫자, 다른 필드는 원본 문자열이며 공란은 빈 문자열입니다. marker_title은 원본 상호와, 중복되지 않을 때 원본 지점명을 결합합니다. 없는 값은 만들지 않았습니다.','','## 중복과 좌표','',f"같은 브랜드·원본 지역·정규화 도로명주소의 복수 행 {S['duplicate_groups']:,}묶음을 보류했습니다. 이 중 묶음 전체의 주소·건물명·위경도 네 원본 문자열이 동일한 것은 {S['same_four_field_groups']:,}묶음입니다. 같은 주소·좌표만으로 삭제/병합하지 않았으며, 층/호/지점명이 다르다는 이유만으로 별도 매장이라고 확정하지도 않았습니다. 다층 사용과 별도 지점의 구분이 미해결인 행은 전부 보류에 원본 그대로 있습니다. 중복 제거 0행, 전체 원본의 반복 bizesId {S['repeated_bizesId_count']:,}개입니다. 반복 ID가 있으면 모든 발생 행을 보류하는 규칙을 적용합니다. 중복 탐지는 단일 브랜드 연결 후보의 같은 도로명주소 기준이며, 주소가 다르게 적힌 실제 동일 업소까지 전수 식별한 것은 아닙니다.",'','좌표는 전체 CSV에서 유한 숫자 여부·누락·위도 -90~90/경도 -180~180 및 한국 주변 점검 사각형(북위32~39.5, 동경124~132)을 검사했습니다. 실제 주소와 좌표의 일치는 역지오코딩/지도 전수 대조하지 않았습니다. 건물 대표좌표와 층·호 누락은 남아 있을 수 있습니다. 원본 주소/좌표를 검색값으로 덮어쓰지 않았습니다.','','| 원본 업종 | 비숫자/누락 | 숫자 범위 오류 | 점검 사각형 밖 |','|---|---:|---:|---:|']
for sec,ss in S['sources'].items():
 c=ss['counts'];L.append(f"| {sec} | {c.get('coordinate_missing_nonnumeric',0):,} | {c.get('coordinate_invalid',0):,} | {c.get('coordinate_outside_screen',0):,} |")
L += ['','## 판단 보류 사유(여러 사유는 중복 집계)','','| 사유 코드 | 행 수 |','|---|---:|']
for reason,n in S['pending_reasons_nonexclusive'].items():L.append(f'| {reason} | {n:,} |')
L+=['','## 검색 근거와 미해결 사항','','**매장별 외부 검색은 일부 사례에 한해서 수행했습니다. 모든 보류 행·브랜드의 개별 검증은 미완료입니다.** 상호 기반 규칙을 통과한 지도 채택도 실제 가맹계약이나 현재 영업을 확인한 확정 명부가 아닙니다. 검색 근거 없이 보류를 해제하지 않았습니다. 검색이 단순 이름 일치만 보여주거나 같은 주소의 등록 단위를 구분하지 못하면 확정이라 쓰지 않았습니다.']
for e in E:
 L+=['','### '+e['topic'],'',e['finding'],'']+['- '+u for u in e['links']]
L+=['','## 검증과 파일 안내','','JSON 재파싱, 카테고리별 모든 브랜드 id/name/순서 보존, 지역 합계와 카테고리 합계, 5개 원본 업종별 합계, 전체 행 분류 합계, 지도 bizesId 유일성, 좌표 숫자·유한성 검사를 통과했습니다. 브랜드 연결 검증은 기준 ID와 매칭/감사기록의 정합성 검사이며 외부 계약관계 확인이 아닙니다.','','- maps/: 기준 카테고리별 JSON 45개(12,498개 브랜드 유지). 음식 관련 빈 파일을 이전 결과에 덮어쓰지 마세요.','- maps_by_source/: 이번 원본 업종별 지도 JSON 5개.','- brand_region_counts.csv: 브랜드·지역별 집계.','- region_audit.csv: 원본 업종·원본 지역별 전체/채택/보류/미검출.','- row_disposition.csv: 원본 1,356,218행 전체의 처리 상태와 출처.','- match_audit.csv: 후보별 브랜드 연결·사유.','- pending_review.jsonl: 보류 행의 원본 전체 필드와 대안 브랜드 목록. JSON Lines이므로 한 줄씩 JSON으로 읽습니다. 대안 목록은 동시 소속을 뜻하지 않습니다.','- duplicate_review.json: 동일 주소 후보 묶음·상태·검색 근거.','- duplicate_removals.csv: 제거 내역(이번에는 헤더만 존재).','- aliases.csv / search_evidence.json / source_manifest.json: 별칭 원천·검색 출처·CSV SHA256 및 원본 manifest.','- summary.json / code/: 처리 수치·검증 결과·재현 코드.','','원본 ZIP별 CSV의 논리적 레코드 번호는 헤더=1 기준입니다. CSV 필드 안 줄바꿈이 있으면 편집기의 물리적 줄 번호와 다를 수 있습니다.']
(D/'review_report.md').write_text('\n'.join(L));(D/'code').mkdir(exist_ok=True)
for n in ['process_remaining.py','finish_remaining.py']:shutil.copy(n,D/'code'/n)
for target,folder in [('remaining_maps_by_category.zip','maps'),('remaining_maps_by_source.zip','maps_by_source')]:
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted((D/folder).glob('*.json')):z.write(p,p.name)
with zipfile.ZipFile('remaining_review_bundle.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(D.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(D))
for target in ['remaining_maps_by_category.zip','remaining_maps_by_source.zip','remaining_review_bundle.zip']:
 with zipfile.ZipFile(target) as z:assert z.testzip() is None
print(json.dumps({'map':S['map_rows'],'pending':S['pending_rows'],'no_candidate':no,'brands':S['brands_with_map_rows'],'sectors':{k:v['counts'] for k,v in S['sources'].items()}},ensure_ascii=False,indent=2))
