import json,csv,collections,os,hashlib,shutil,zipfile
from pathlib import Path
D=Path('deliverables');S=json.load(open(D/'summary.json'));P=json.load(open('profile.json'));B=P['brands'];pending=json.load(open(D/'pending_review.json'));dups=json.load(open(D/'duplicate_review.json'))
def dump(n,o):
 (D/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False))
E=[]
def evidence(key,topic,urls,observation,decision,lines=None,scope='브랜드별칭검토',query=None):
 E.append(dict(evidence_id=key,checked_date='2026-10-28',topic=topic,source_links=urls,observation=observation,decision=decision,csv_lines=lines or [],scope=scope,search_query=query))
evidence('E01','메가커피 / 메가MGC커피',['https://www.mega-mgccoffee.com/store/find/','https://www.mega-mgccoffee.com/bbs/detail/?YmJzX2lkeD0xNTImYmJzX2NhdGVnb3J5PTQmYmJzX2RldGFpbF9jYXRlZ29yeT0mYmJzX3BhZ2U9Mg=%3D'],'공식 매장찾기의 메가MGC커피 표기와 공식 FAQ의 메가커피 표기를 대조.','동일 기준 ID의 명칭 변형으로 허용. 개별 매장 전수 대조 아님.')
evidence('E02','이디야 / 이디야커피',['https://www.ediya.com/contents/find_store.html'],'공식 매장검색에서 이디야 명칭 사용.','이디야 약칭 허용. 실제 가맹관계 전수 확인 아님.')
evidence('E03','할리스 / 할리스커피',['https://www.hollys.co.kr/store/korea/korStore.do'],'공식 매장검색에서 할리스 및 주소의 할리스커피 표기 확인.','동일 기준 ID에 두 표기를 허용.')
evidence('E04','탐앤탐스 / TOM N TOMS',['https://www.tomntoms.com/'],'공식 사이트의 한영 브랜드 표기를 대조.','탐앤탐스커피 기준 ID의 약칭 허용.')
evidence('E05','텐퍼센트',['https://www.tenpercentcoffee.co.kr/','https://introduce.tenpercent.paycrux.co.kr/'],'공식 브랜드/주문안내에서 텐퍼센트커피 및 TENPERCENTCOFFEE 표기를 확인.','기준명 텐퍼센트스페셜티커피의 약칭 허용. 지점별 확인 아님.')
evidence('E06','달콤',['https://www.dalkomm.com/findStore','https://www.dalkomm.com/danalIntro'],'달콤과 달콤.N의 구분이 보임. 달콤커피 표기도 사용됨.','달콤커피는 검토별칭. 달콤 단독은 일반명 위험으로 보류. 달콤.N은 별도 기준 브랜드와 구분.')
evidence('E07','원유로',['https://play.google.com/store/apps/details?hl=ko&id=com.wmpoplus.oneeurocoffee','https://app.passorder.co.kr/normal/6fb3aa52-4c84-4a5c-9ce9-16c8d55cd9f8'],'공식 앱 제목의 스페셜티 명칭과 주문서비스의 원유로커피 표기를 대조.','원유로커피를 기준명에 연결하는 별칭으로 허용. 매장별 영업 확인 아님.')
evidence('E08','매머드 두 브랜드',['https://mmthcoffee.com/sub/faq.html?faqCate=6','https://www.mmthcoffee.com/sub/store.html'],'공식 FAQ에서 매머드커피와 매머드익스프레스를 구분.','두 기준 ID를 합치지 않음. 매머드커피익스프레스 표기는 익스프레스에 연결. 매머드커피 명칭만으로 실제 매장형태를 보장하지 않음.')
evidence('E09','바리스텔라의 과거명 문제',['https://www.newsis.com/view/NISX20150423_0013619100','https://www.topdaily.kr/articles/110645?ref_sec=a_ser'],'공개 기사에서는 카페베네와 바리스텔라를 별도/병행 브랜드로 다룸.','입력 history/name_variants에 카페베네가 있어도 현재 바리스텔라 매장으로 자동 채택하지 않음.',scope='과거명연결위험검토')
evidence('E10','더커피 동명이인',['https://www.the-coffee.co.kr/','https://jumpoline.com/franch/FranchView.aspx?frnc=20241537','https://choboss.com/brand/더커피the-coffee-wxqg'],'기준 파일에 대소문자만 다른 더커피 2개 ID 존재. 검색 결과의 법인/브랜드 이력도 단일 식별 근거가 되지 못함.','상호나 영문 대소문자로 ID를 선택하지 않고 보류.',scope='복수ID검토')
evidence('E11','오슬로우의 두 ID',['https://pchanet.kr/brand/BRD_20250535','https://pchanet.kr/brand/BRD_20190591'],'기준 파일에 오슬로우와 오슬로우 영호남이 별도 ID. 공개 가맹정보에도 별도 항목 존재.','지역만 보고 ID를 배분하지 않음. 일반 오슬로우 표기는 보류.',scope='복수ID검토')
evidence('E12','짧은 이름의 추가 검토',['https://dancingcup.co.kr/bbs/content.php?co_id=shop','https://appledangcafe.co.kr/landing/','https://www.hisffee.com/store/','https://www.coffeehole.co.kr/'],'공식 브랜드/매장 안내에서 댄싱컵, 사과당, 히스피, 커피홀 명칭 확인.','3글자 일괄보류의 예외로 명시적 허용. 카페 업종 및 지점 규칙 통과를 함께 요구.')
evidence('E13','경희대 컴포즈 3개 지점',['https://give.khu.ac.kr/data/file/data_01/2942980483_4m06iprk_0f2530262072e8695d761bfb5695b2abd396d2ad.pdf'],'대학 공식 연차보고서의 검색 색인에서 외국어대학관점, 전자국제점, 국제캠퍼스기숙사점의 서로 다른 명칭을 확인. 원문 PDF는 49,974,039바이트 용량 제한으로 직접 열기 실패.','CSV의 3개 명칭을 별도 행으로 보존. 주소/좌표 동일로 병합하지 않음. 현재 동시영업이나 실제 좌표를 확정한 것은 아님.',[555030,749300,754865],'중복검토','경희대학교 컴포즈커피 외국어대학 전자정보 기숙사')
evidence('E14','파스쿠찌 가천대/가천관',['https://www.pascucci.co.kr/store/storeList.asp?page=47','https://place.clariosync.com/p/7179790/파스쿠찌-가천관점'],'공식 검색 색인의 가천대점은 비전타워, 공개 장소의 가천관점은 가천관 B동 지하1층. CSV 층값은 두 행 모두 1로, 공개 자료와 차이 존재. 공식 페이지는 개편되어 같은 항목 재조회에 한계.','별도 지점 가능성이 있으나 층정보 충돌을 포함해 두 행 모두 보류. 원본 값을 수정하거나 합치지 않음.',[108621,723738],'중복검토','파스쿠찌 가천관점 / 파스쿠찌 가천대점 비전타워')
evidence('E15','블루포트 신성대학교',['https://www.diningcode.com/list.dc?query=충남+당진시+정미면+대학로','https://www.fnnews.com/news/202603300911582797'],'공개 장소 목록에 두 이름이 있으나 대학 카페 관련 보도만으로 두 상가ID가 별도 매장인지 판별 불가.','두 행 모두 보류. 두 검색 결과가 있다는 이유로 별도 매장 확정하지 않음.',[79754,421583],'중복검토','블루포트 신성대 학생회관')
evidence('E16','블루포트 충남대의대점',['https://m.albamon.com/jobs/detail-company/C7rE4CkolMSdeNpzib2a2A%3D%3D'],'공개 사업장 안내에서 문화로266 의행관 학생회관 1층을 확인. 같은 이름/주소인 두 CSV행의 관계는 미확인.','유사중복 가능성만 남기고 두 행 보류. 하나를 삭제하지 않음.',[69364,830139],'중복검토','블루포트 충남대의대점')
evidence('E17','경성대 이디야',['https://cafe.ayo.pe.kr/cafe/region/부산/남구/대연동','https://kyungsung.ac.kr/ipsi/CMS/CampusMgr/list.do?mCode=MN077'],'공개 목록에서 중앙도서관점 6층, 대학 지도에서 건물 구분 확인. 대학본부점과의 동시영업/ID관계까지 확인되지 않음.','서로 다른 지점명과 층은 보존하되 이번 지도 채택에서는 두 행 보류.',[210531,236294],'중복검토','경성대 이디야 중앙도서관 대학본부')
evidence('E18','사과당 마곡점 비카페 업종',['https://appledangcafe.co.kr/landing/','https://bizsurfing.com/서울/강서구/마곡동/카페'],'공식 페이지에서 마곡점 명칭, 공개 장소 목록에서 공항대로186을 확인. CSV의 상호/지점/주소와 대조.','CSV 빵/도넛 분류만으로 배제하지 않고 지도 채택. 현재 가맹계약/영업 여부까지 확인한 것은 아님.',[727478],'비카페업종검토','사과당 마곡 공항대로186')
evidence('E19','디저트39 송도캠퍼스타운점 비카페 업종',['https://cafe.ayo.pe.kr/snack/aa61ecdfa3c8176954134c0b59e43c1d','https://findby.co.kr/details/21982-281854256368-st-652b67c58c641f9e38a57888'],'공개 장소 정보의 지점명과 송도과학로27번길55가 CSV와 부합. 원본에는 같은 주소의 중복 가능 행도 있음.','단순 업종 오분류 가능성은 있으나 중복관계가 해소되지 않아 보류.',[829211],'비카페업종및중복검토','site.dessert39.com 송도캠퍼스타운 / 디저트39 송도캠퍼스타운점')
evidence('E20','동네커피 일반명 검토',['https://www.dongnae-coffee.com/?code=120846333&page_code=otherpage','https://cafe.ayo.pe.kr/cafe/78eece715d82c7b76e71a9bd6f5b0ba3','https://app.passorder.co.kr/advance/88836fa4-d4c5-4698-8c13-1165261942b1'],'공식 가호점 안내와 공개 장소의 주소는 가호로8로 같으나 공식은 1층, 공개 장소는 2층.','동네커피라는 이름만으로 전부 연결하지 않음. 층 차이는 원본을 임의 수정할 근거가 아니므로 보류 유지.',scope='일반명및층정보검토',query='동네커피 가호점 공식')
dump('search_evidence.json',E)
for g in dups:
 lines={x['csv_line'] for x in g['rows']}
 refs=[e for e in E if lines.intersection(e['csv_lines'])]
 if refs:
  g['evidence_ids']=[e['evidence_id'] for e in refs];g['source_links']=list(dict.fromkeys(u for e in refs for u in e['source_links']));g['search_status']='개별검색검토';g['search_conclusion']=' | '.join(e['decision'] for e in refs)
dump('duplicate_review.json',dups)
for x in pending:
 refs=[e for e in E if x['csv_line'] in e['csv_lines']]
 x['evidence_ids']=[e['evidence_id'] for e in refs]
 x['search_status']='개별검색검토' if refs else '개별매장외부검색미실시'
 x['review_priority']='브랜드연결후보' if x['match_basis'] else '광범위문자열탐색'
dump('pending_review.json',pending)
strongpending=sum(bool(x['match_basis']) for x in pending);weakpending=len(pending)-strongpending
S.update(pending_strong_rows=strongpending,pending_lexical_only_rows=weakpending,external_evidence_entries=len(E),externally_reviewed_csv_lines=len(set(n for e in E for n in e['csv_lines'])),coordinate_validation={'checked_rows':S['source_rows'],'numeric_missing_or_nonfinite':0,'global_range_errors':0,'outside_screen_32_39_5N_124_132E':0,'address_coordinate_geocoding_checked':False})
# counts are per source row, not per candidate brand (candidate-brand counts can overlap)
byline={x['csv_line']:x for x in pending};audit={int(x['csv_line']):x for x in csv.DictReader(open(D/'match_audit.csv',encoding='utf-8-sig'))}
source_regions=collections.Counter();map_regions=collections.Counter();pending_regions=collections.Counter();none_regions=collections.Counter();state=collections.Counter()
with open(D/'row_disposition.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['csv_line','bizesId','ctprvnNm','status','brand_id','review_priority'])
 with zipfile.ZipFile('upload/records.zip') as z:
  import io
  for line,r in enumerate(csv.DictReader(io.TextIOWrapper(z.open('records.csv'),encoding='utf-8-sig')),2):
   a=audit.get(line);st=a['status'] if a else 'no_candidate';state[st]+=1;source_regions[r['ctprvnNm']]+=1
   priority=byline[line]['review_priority'] if line in byline else ''
   w.writerow([line,r['bizesId'],r['ctprvnNm'],st,a['brand_id'] if a else '',priority])
   (map_regions if st=='map' else pending_regions if st=='pending' else none_regions)[r['ctprvnNm']]+=1
with open(D/'region_audit.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['source_region','source_rows','map_rows','pending_rows','no_candidate_rows'])
 for r,n in source_regions.items():w.writerow([r,n,map_regions[r],pending_regions[r],none_regions[r]])
with open(D/'duplicate_removals.csv','w',encoding='utf-8-sig',newline='') as f:
 csv.writer(f).writerow(['kept_csv_line','removed_csv_line','kept_bizesId','removed_bizesId','reason'])
# Alias registry with approved vs candidate-only provenance.
confirmed={238:['메가커피','메가MGC커피','메가엠지씨커피','megacoffee'],545:['이디야','EDIYA'],819:['할리스커피','HOLLYS','HOLLYSCOFFEE'],747:['탐앤탐스','TOMNTOMS'],755:['텐퍼센트커피','텐퍼센트','TENPERCENTCOFFEE'],232:['매머드커피익스프레스','매머드익스프레스'],116:['달콤커피'],531:['원유로커피']}
# Use build.py's exact normalization and registry without executing its pipeline again.
import ast
src=ast.parse(Path('build.py').read_text());defs=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='norm'];env={};exec('import unicodedata,html',env);exec(compile(ast.Module(body=defs,type_ignores=[]),'norm','exec'),env);norm=env['norm'];C={(i,norm(a)) for i,ss in confirmed.items() for a in ss}
with open(D/'alias_registry.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['normalized_alias','brand_id','brand_name','provenance','identity_alias_status'])
 for a,entries in P['aliases'].items():
  for i,k in entries:w.writerow([a,B[i]['id'],B[i]['name'],k,'eligible_subject_to_ambiguity_and_row_checks' if k in ['catalog','english'] or (i,a) in C else 'candidate_only'])
mapdata=json.load(open(D/'cafe_map.json'));mapids={m['bizesId'] for b in mapdata for ms in b['regions'].values() for m in ms};pendingids={x['source_row']['bizesId'] for x in pending}
assert not mapids&pendingids
assert state['map']==S['map_rows'] and state['pending']==S['pending_rows'] and state['no_candidate']==S['no_candidate_rows']
assert sum(source_regions.values())==S['source_rows']==sum(state.values())
# Verify every emitted value and brand attachment against the exact source candidate row.
lookup={x['row']['bizesId']:x for x in P['rows']};audid={x['bizesId']:x for x in audit.values()}
for b in mapdata:
 for region,stores in b['regions'].items():
  for m in stores:
   a=audid[m['bizesId']];r=lookup[m['bizesId']]['row']
   assert a['brand_id']==b['id'] and a['status']=='map'
   for k in ['rdnmAdr','bldNm','bizesNm','brchNm','ctprvnNm','signguNm','dongNo','flrNo','hoNo']:assert m[k]==r[k]
   assert m['lat']==float(r['lat']) and m['lon']==float(r['lon'])
for p in D.glob('*.json'):json.load(open(p))
S['validation']={'json_parse_all':'PASS','all_842_id_name_pairs_preserved':'PASS','map_source_fields_and_brand_audit_consistency':'PASS','unique_map_bizesId':'PASS','map_pending_disjoint':'PASS','region_map_sum_equals_map_rows':'PASS','all_source_row_dispositions_sum':'PASS','coordinates_numeric_and_finite':'PASS'}
dump('summary.json',S)
# Human report, with links relative to the review bundle contents.
lines=[]
def put(s=''):lines.append(s)
put('# 프랜차이즈 카페 지도 데이터 검토 보고서');put();put('처리일: 2026-10-28. 자료: records.zip 내부 records.csv와 brands_by_category.zip 내부 카페.json. 다른 업종 JSON의 브랜드는 추가하지 않았습니다.');put()
put('## 결과와 해석');put();put('이 결과는 **상호명 기반의 보수적 지도 채택본**입니다. 실제 가맹계약, 현재 영업, 과거와 현재의 운영 주체를 전수 확인한 확정 명부가 아닙니다. 불확실한 행은 삭제하지 않고 별도 검토 파일로 남겼습니다. 검색은 아래 근거 항목과 해당 행에 한해 수행했으며, 보류 전체를 개별 검색한 것은 아닙니다.');put()
put('| 구분 | 행 수 |');put('|---|---:|')
for k,v in [('CSV 원본 전체',S['source_rows']),('지도 채택',S['map_rows']),('보류: 연결 규칙을 통과했으나 추가 검토 필요',strongpending),('보류: 과거명·약칭·부분문자열 등 광범위 탐색만 일치',weakpending),('후보 미검출',S['no_candidate_rows']),('지도 미포함 합계(보류 포함)',S['not_in_map_rows']),('중복 제거',0)]:put(f'| {k} | {v:,} |')
put();put(f"원본 {S['source_rows']:,} = 지도 {S['map_rows']:,} + 보류 {S['pending_rows']:,} + 후보 미검출 {S['no_candidate_rows']:,}. 브랜드 842개를 순서·id·name 그대로 유지했습니다. 매장 행이 있는 브랜드는 {S['brands_with_map_rows']}개, 나머지 {842-S['brands_with_map_rows']}개는 모든 지역이 빈 배열입니다. 이름이 null인 coffee_20240319도 그대로 유지하고 매장을 배정하지 않았습니다.")
put();put('**후보 미검출은 해당 브랜드가 아니라고 확인한 수가 아닙니다.** 탐색 사전에 없는 오탈자·약칭·법인명만 기재된 매장은 놓칠 수 있습니다. 광범위 탐색 보류에는 이름 일부가 우연히 같은 무관 업소가 많이 포함되어 있습니다. 보류 수를 실제 프랜차이즈 매장 수로 읽으면 안 됩니다.');put()
put('## 데이터 구조와 원본 보존');put();put('cafe_map.json의 최상위는 배열이며 각 객체는 id, name, regions만 갖습니다. regions는 기준 17개 지역과 원본 특수값 1개를 합친 18개 키를 모든 브랜드에 동일하게 둡니다. 매장에는 rdnmAdr, bldNm, lat, lon, bizesId, bizesNm, brchNm, ctprvnNm, signguNm, dongNo, flrNo, hoNo, marker_title을 넣었습니다. lat/lon은 유한한 JSON 숫자, 나머지는 원본 문자열입니다. 원본 공란은 빈 문자열이며 추정으로 채우지 않았습니다.');put();put('marker_title은 원본 bizesNm을 쓰고, 정규화 비교에서 지점명이 이미 포함되어 있지 않을 때만 원본 brchNm을 공백으로 이어 붙였습니다. 원본 주소·층·호·좌표는 검색 자료로 덮어쓰지 않았습니다. 매출·매장 수 history 통계는 매장 좌표로 사용하거나 결과에 복사하지 않았습니다.');put()
put('## 매칭 규칙');put();put('공백·기호·HTML 엔티티·영문 대소문자·악센트를 정규화하고 한영 병기 괄호 안팎을 별칭으로 추출했습니다. 전체 상호 일치, 기준 이름 뒤의 지점 표기, 원본 주소/행정동/건물/지점명에 있는 지역 단서가 뒷부분을 설명하는 경우를 연결 후보로 보았습니다. 이름이 중간에 들어있다는 이유만으로 지도에 넣지 않았습니다. 가장 구체적인 이름이 일치할 때 하위 브랜드를 우선하되, 동일 별칭이 복수 ID에 해당하면 자동 선택하지 않았습니다.');put();put('짧거나 일반적인 이름, 명시적 과거명, 복합상호, 기준에 없는 하위 브랜드 표기, 시설·공장 가능성, 비카페 업종은 추가 검토 사유입니다. 단어가 일반적인지에 대한 명시적 보수 목록과 짧은 이름 허용 목록은 build.py에 공개했습니다. 이 목록은 의미 판정을 완전 자동화하거나 정확도를 통계적으로 입증한 것이 아닙니다. 별칭 원천/허용 상태는 alias_registry.csv, 행별 적용 근거는 match_audit.csv에 있습니다. 약칭 후보를 모두 허용하지 않았습니다.');put();put('history에 들어있는 카페베네 등을 현재 바리스텔라로 일괄 연결하지 않았습니다. 더커피(The coffee)와 더커피(the coffee)는 ID가 다르며 대소문자로 구분하지 않았습니다. 오슬로우의 두 ID 역시 지역으로 임의 배분하지 않았습니다. name=null인 브랜드의 과거 이름만으로 매장을 할당하지 않았습니다.');put()
put('## 지역 처리');put();put('원본 ctprvnNm에는 16종이 있고, 광주광역시·전라남도는 별도 값으로 나타나지 않습니다. **전남광주통합특별시 55,881행은 실제 CSV 값**입니다. 현재 행정구역이라는 법적 판단을 하지 않았고, 시군구·주소를 보고 광주/전남으로 나누지 않았습니다. 원본 ctprvnNm도 매장 안에 그대로 보존합니다.');put();put('서울특별시→서울, 부산광역시→부산, 대구광역시→대구, 인천광역시→인천, 대전광역시→대전, 울산광역시→울산, 세종특별자치시→세종, 경기도→경기, 강원특별자치도→강원, 충청북도→충북, 충청남도→충남, 전북특별자치도→전북, 경상북도→경북, 경상남도→경남, 제주특별자치도→제주로 이름만 대응했습니다. 전남광주통합특별시는 동일한 키로 보존했습니다. 광주·전남의 빈 배열은 매장이 없다는 뜻이 아니라 원본 지역을 분리 배정하지 않았다는 뜻입니다.');put();put('| regions 키 | 지도 행 수 |');put('|---|---:|')
for r,n in S['map_region_counts'].items():put(f'| {r} | {n:,} |')
put(f"| 합계 | {S['map_rows']:,} |");put();put('원본 지역별 전체·채택·보류·미검출은 region_audit.csv에, 브랜드 842개 각각의 지역별 합계는 brand_region_counts.csv에 있습니다.');put()
put('## 중복과 동일 주소');put();put(f"전체 CSV의 bizesId는 모두 서로 달랐습니다(동일 ID 복수행 0). 완전 동일 원본행도 없으므로 제거한 행은 0이며 duplicate_removals.csv는 헤더만 있습니다. 주소·건물명·좌표가 같다는 이유로 합친 행도 0입니다.");put();put(f"단일 브랜드 연결 후보들에서 같은 브랜드·원본 지역·정규화 도로명주소의 복수행을 {S['duplicate_groups']:,}묶음 탐지했습니다. 이 중 묶음 전체의 주소·건물명·좌표 네 원본 문자열이 모두 같은 것은 {S['same_four_field_groups']:,}묶음입니다. {S['duplicate_pending_groups']:,}묶음은 동일 매장/다층 사용/별도 매장 구분을 확정할 수 없어 보류했습니다. 한 묶음의 경희대 컴포즈 3행은 공식 검색 색인의 서로 다른 지점명과 CSV 지점 표기를 근거로 각각 보존했습니다. 이것도 현재 동시영업 확인은 아닙니다.");put();put('duplicate_review.json은 모든 탐지 묶음에 원본 39개 열과 CSV 행 번호, 상태, 이유, 검색 여부를 남깁니다. 주소가 같은 다른 건물·대학교 내부 매장과 여러 층을 쓰는 한 매장을 자동 판정하지 않았습니다. 층이나 호가 다르다는 사실만으로 별도 매장으로 확정하지 않았습니다. 현재 탐지는 단일 브랜드 연결 후보의 같은 주소를 기준으로 하므로, 이름이 불명확한 보류·주소가 다르게 기재된 동일 매장·도로명주소가 다른 인접 건물까지 모두 찾아낸 결과는 아닙니다.');put();put('이전 제거 289행과 추가 병합 174행은 개별 행 목록이 첨부되지 않아 이번 원본 행과 1:1 대응시킬 수 없습니다. 이전 결과를 재사용하지 않고 CSV 전체를 다시 읽었으며, 이전 숫자에 맞추는 제거·복원은 하지 않았습니다. 이전의 147/12/11묶음 판단을 아는 것으로 가정하지 않았습니다.');put()
put('## 보류 사유와 비카페 업종');put();put('| 사유 코드 | 해당 행 수(중복 집계) |');put('|---|---:|')
for r,n in S['pending_reason_counts'].items():put(f'| {r} | {n:,} |')
put();put('사유가 여러 개인 행은 위 표에 여러 번 집계됩니다. pending_review.json에는 각 행의 원본 전체 열, 대안 브랜드 ID/name 목록, 사유, 우선순위, 외부 검색 여부를 남겼습니다. 대안 브랜드들은 동시에 속한다는 뜻이 아닙니다. 카페가 아닌 CSV 업종도 처음부터 제외하지 않았으며, 사과당 마곡점 1행은 공식 명칭+공개 주소 대조로 채택했습니다. 나머지는 근거가 부족하거나 별도 중복 문제가 있어 보류했습니다. 디저트39 송도캠퍼스타운점처럼 비카페 업종이라도 이름과 주소가 실제 카페 안내와 부합하는 예가 있어 업종만으로 배제할 수 없습니다.');put()
put('## 좌표와 주소');put();put(f"CSV {S['source_rows']:,}행 전체에서 lat/lon 누락·비숫자·비유한 값 0행, 위도 -90~90/경도 -180~180 범위 오류 0행, 한국 주변 점검 사각형(북위32~39.5, 동경124~132) 밖 0행입니다. 이 사각형 검사는 행정경계나 영업장 실제 위치 검증이 아닙니다. 지도 채택 행의 좌표를 숫자로 변환한 뒤 원본 숫자값과 다시 비교했습니다.");put();put('**실제 주소와 좌표가 일치하는지 역지오코딩 또는 지도 전수 대조는 하지 않았습니다.** 건물 대표좌표를 공유하거나 층·호가 잘못된 행일 수 있습니다. 공개 장소의 층이 CSV와 다른 사례는 보고서 근거에 남기고 원본을 바꾸지 않았습니다.');put()
put('## 외부 검색 근거와 한계');put();put(f"검토 근거 {len(E)}항목이며 CSV 개별 행 {S['externally_reviewed_csv_lines']}개와 연결된 항목이 있습니다. 브랜드 별칭에 대한 검색은 해당 브랜드의 모든 매장을 조회했다는 뜻이 아닙니다. 검색 결과가 없거나 동적 페이지/용량제한으로 확인하지 못하면 확정으로 쓰지 않았습니다. 보류 행 전체에 대한 외부 검색은 미완료이며, 각 행에 미실시 상태를 표시했습니다.");put()
for e in E:
 put(f"### {e['evidence_id']} — {e['topic']}");put();put(e['observation']);put();put('판단: '+e['decision']);put()
 for u in e['source_links']:put('- '+u)
 put()
put('## 검증 및 파일 안내');put();put('JSON 재파싱, 842개 id/name 쌍·순서 일치, 매장 원본 필드 일치, 행별 브랜드 연결 감사기록 일치, 지도 bizesId 유일성, 지도·보류 행의 분리, 지역 합계·브랜드 합계·전체 원본 분류 합계 일치를 검사해 모두 통과했습니다. **브랜드 연결 검사란 입력 기준 ID와 매칭 규칙/감사기록의 일치 검사이며, 외부 가맹계약을 검증했다는 뜻이 아닙니다.**');put()
for n,desc in [('cafe_map.json','지도용 채택 데이터'),('summary.json','수치와 검증 결과'),('brand_region_counts.csv','842개 브랜드의 지역별 집계'),('region_audit.csv','원본 지역별 처리 합계'),('match_audit.csv','문자열 후보 69,090행의 처리 이유'),('row_disposition.csv','840,254행 전체의 처리 상태'),('pending_review.json','미확정 후보 및 원본 전체 열'),('duplicate_review.json','동일 주소 묶음과 검색 근거'),('duplicate_removals.csv','삭제 내역(이번에는 0행)'),('alias_registry.csv','별칭 사전과 출처 유형'),('search_evidence.json','검색 근거와 행 연결'),('source_manifest.json','입력 파일 식별 해시'),('code/','재현 코드')]:put(f'- `{n}`: {desc}')
put();put('CSV 행 번호는 헤더를 1행으로 세는 csv.reader의 논리적 레코드 번호입니다. 여러 줄을 포함한 CSV 필드가 있을 경우 텍스트 편집기의 물리적 줄 번호와 다를 수 있습니다. UTF-8-SIG CSV와 UTF-8 JSON/Markdown을 사용했습니다.');put()
(D/'review_report.md').write_text('\n'.join(lines))
(D/'code').mkdir(exist_ok=True)
for n in ['profile.py','build.py','finalize.py']:shutil.copy(n,D/'code'/n)
(D/'code'/'README.md').write_text('원본 두 ZIP을 작업 폴더 upload/에 둡니다. Python 표준 라이브러리만 사용합니다.\n\n1. brands_by_category.zip의 카페.json을 cafe_source.json으로 추출합니다(UTF-8).\n2. python profile.py\n3. python build.py\n4. python finalize.py\n\n입력 순서와 ID를 원본 해시로 고정했습니다. 외부 검색의 판단은 코드/보고서에 명시적으로 기록되어 있으며 재실행으로 최신 영업정보를 자동 조회하지 않습니다.\n')
manifest={}
for n in ['upload/records.zip','upload/brands_by_category.zip','cafe_source.json']:
 path=Path(n);manifest[n]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
dump('source_manifest.json',manifest)
# Final deliverable must remain strict JSON.
for p in D.glob('*.json'):json.load(open(p))
print(json.dumps({'summary':S,'sizes':{p.name:p.stat().st_size for p in D.iterdir() if p.is_file()}},ensure_ascii=False,indent=2))
