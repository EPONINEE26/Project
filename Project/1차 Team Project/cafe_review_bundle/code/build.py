import json,csv,collections,re,math,os,unicodedata,html,hashlib,zipfile
P=json.load(open('profile.json'));B=P['brands'];A=P['aliases']
def norm(s):
 s=unicodedata.normalize('NFKD',html.unescape(s or '')).casefold()
 return ''.join(c for c in unicodedata.normalize('NFC',''.join(c for c in s if not unicodedata.combining(c))) if c.isalnum())
# Source-name aliases are not assertions of current franchise membership.
confirmed={238:['메가커피','메가MGC커피','메가엠지씨커피','megacoffee'],545:['이디야','EDIYA'],819:['할리스커피','HOLLYS','HOLLYSCOFFEE'],747:['탐앤탐스','TOMNTOMS'],755:['텐퍼센트커피','텐퍼센트','TENPERCENTCOFFEE'],232:['매머드커피익스프레스','매머드익스프레스'],116:['달콤커피'],531:['원유로커피']}
confirmed={(i,norm(a)) for i,vs in confirmed.items() for a in vs}
shortsafe=set('이디야 댄싱컵 사과당 히스피 커피홀 더벤티 빽다방 할리스 더리터 블루샥 드롭탑 떼루와 커피쿡 맷차 차눙 캔모아 커피니 파스쿠찌 엔제리너스 부바스 고바슨 마시그래이 바빈스 바나프레소 콩카페'.split())
generic=set('감성카페 감성커피 동네커피 동백다방 동백커피 더원커피 더커피 더카페 더블업 대한커피 별난커피 바로커피 마실커피 만족커피 멀티커피 무무커피 무인다방 뜰커피 남대문커피 광화문커피 감성카페 고고카페 그린머그 그린힐커피 그림카페 데니스 디커피 라마 라떼떼 루고 몰타 보니또 카페보니또 생활커피 서로커피 설화카페 슈퍼커피 시선 식물학 심재 아는커피 아리스타 아마떼 아재커피 아토커피 알리바바 어니스트 언더스탠딩 에센스커피 엔커피 영커피 여유한잔 오픈커피 온누리커피 올차 왓커피 운커피 위너스커피 이구아나 일상엔 자몽자몽 저스틴 점프 정글비 젬스톤 조선다방 주식커피 진심커피 채우다 카페콘크리트 카페그란데 카페달링 카페머물다 카페몬스터 카페리프 카페마틸다 카페비엔나 카페소프트 카페수르 카페오를리 카페온나 카페포코 카페폴 캐롤커피 커피나무 커피나인 커피는 커피다운 커피스토어 커피아트 커피왕 커피코트 커피팡 켄커피 클로버커피 테이블스 트리고 퍼스트커피 평화다방 풋풋 프롬프트 피크니크 하이커피 핸드메이드 휴게소'.split())
manual_generic={'PLAN플랜','PRESENT프레전트','chilling','ifcoffee','jaycoffee','GRABCOFFEE','BETTERBEAN','THEBLUECOFFEE','GREENYDAY','COFFEEPUCK','DOLTA','Bara1998','Pause10'}
generic.update(map(norm,manual_generic))
generic.update('plan present select milo above honest jump eat gt asa ncc bemu sell pause chilling'.split())
R={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','전남광주통합특별시':'전남광주통합특별시'}
regions=['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주','전남광주통합특별시']
# Explicit whitelist is reviewed separately from derived abbreviation candidates.
def strength(i,a):
 kinds={k for j,k in A[a] if j==i}
 if 'catalog' in kinds or 'english' in kinds:return '기준명/한영병기'
 if (i,a) in confirmed:return '검색검토별칭'
 return None

def generic_brand(i,a):
 b=B[i]; outer=norm(re.sub(r'\([^)]*\)','',b['name'] or ''))
 return (outer in generic or a in generic or (len(a)<=3 and a not in shortsafe) or i in [144,145,491,492,841])

def shape(r,s,p,q,a):
 # Only whole normalized name or a prefix followed by corroborated location/branch.
 if p!=0:return None
 tail=s[q:]
 if not tail:return '상호전체일치'
 if tail in ['커피','카페','coffee','cafe']:return '기준명+업태어'
 if tail.endswith('점') and 1<len(tail)<=24 and not any(t in tail for t in ['컴퍼니','로스터','학원','공장','본사','물류','엔터테인먼트']):return '기준명+지점표기'
 loc=[r[k] for k in ['ctprvnNm','signguNm','adongNm','ldongNm','rdnm','bldNm','brchNm'] if r[k]]
 tokens=set()
 for t in loc:
  for token in re.split(r'\s+',t):
   n=norm(token)
   if len(n)>=2:tokens.add(n)
   n=re.sub(r'(특별자치시|특별자치도|특별시|광역시|[시군구동읍면리])$','',n)
   if len(n)>=2:tokens.add(n)
 if len(tail)>=2 and any(tail==t or tail.startswith(t) for t in tokens):return '기준명+원본지역단서'
 return None

items=[]
for x in P['rows']:
 r=x['row']; s=norm(r['bizesNm']); eligible=[];strong=[]
 for p,q,a in x['hits']:
  sh=shape(r,s,p,q,a)
  for i,k in A[a]:
   st=strength(i,a)
   if st and sh:strong.append((i,p,q,a,sh,st))
 # Prefer most specific complete name over embedded parent aliases; equal-length IDs remain ambiguous.
 if strong:
  mx=max(t[2]-t[1] for t in strong);eligible=[t for t in strong if t[2]-t[1]==mx]
  ids=sorted(set(t[0] for t in eligible))
 else:ids=[]
 reasons=[];chosen=None;basis=''
 if len(ids)>1:reasons.append('동일상호가복수브랜드ID에해당')
 elif len(ids)==1:
  chosen=ids[0];v=next(t for t in eligible if t[0]==chosen);basis=v[4]+' / '+v[5]
  if generic_brand(chosen,v[3]):reasons.append('짧거나일반적인이름또는ID식별불가')
  if r['indsSclsNm']!='카페':reasons.append('CSV비카페업종추가확인필요')
  tail=s[v[2]:]
  if any(tail.startswith(t) for t in ['익스프레스','스마트카페','테라스','미니','연구실','물류','공장','키친']):reasons.append('하위브랜드또는비매장시설추가확인필요')
  if any(c in r['bizesNm'] for c in ['&','＆',',','，']) and tail:reasons.append('복합상호추가확인필요')
 else:
  # Keep every weak substring candidate separate; no inferred identity from containment.
  ks={k for p,q,a in x['hits'] for i,k in A[a]}
  if 'history' in ks:reasons.append('과거명또는부분포함만일치현재브랜드연결미확인')
  else:reasons.append('부분포함약칭또는지점표기불명확')
 try:
  lat=float(r['lat']);lon=float(r['lon'])
  if not all(map(math.isfinite,[lat,lon])) or not(-90<=lat<=90 and -180<=lon<=180):reasons.append('좌표숫자범위오류')
  elif not(32<=lat<=39.5 and 124<=lon<=132):reasons.append('한국주변좌표범위밖')
 except ValueError:reasons.append('좌표누락비숫자');lat=lon=None
 if not r['rdnmAdr']:reasons.append('도로명주소누락')
 allids=sorted(set(i for p,q,a in x['hits'] for i,k in A[a]))
 items.append({'line':x['line'],'row':r,'brand_index':chosen,'candidate_indices':ids or allids,'reasons':reasons,'basis':basis,'lat':lat,'lon':lon})
# Reviewed non-cafe exception: official branch name + public address agree.
for x in items:
 if x['line']==727478 and x['brand_index']==353:
  x['reasons']=[r for r in x['reasons'] if r!='CSV비카페업종추가확인필요']
  x['basis']+=' / 공식사과당마곡점명칭+공개장소공항대로186대조;영업여부미확인'
# Address grouping for accepted candidates, preserving all source records.
groups=collections.defaultdict(list)
for x in items:
 if x['brand_index'] is not None:
  groups[(x['brand_index'],x['row']['ctprvnNm'],norm(x['row']['rdnmAdr']))].append(x)
duplicates=[]
for key,g in groups.items():
 if len(g)<2:continue
 names=[norm(x['row']['bizesNm']+' '+x['row']['brchNm']) for x in g]
 # Different labels can be truncated names of one shop; substring pairs stay pending.
 distinct=len(set(names))==len(names) and all(a not in b and b not in a for i,a in enumerate(names) for b in names[i+1:])
 same4=len(set(tuple(x['row'][k] for k in ['rdnmAdr','bldNm','lat','lon']) for x in g))==1
 verified_campus={555030,749300,754865}
 verified=set(x['line'] for x in g)==verified_campus
 status='공식목록의서로다른지점명보존' if verified else '동일매장여부보류'
 if not verified:
  for x in g:x['reasons'].append('동일브랜드동일주소중복가능다층사용포함미확인')
 duplicates.append({'group_id':'D'+str(len(duplicates)+1).zfill(5),'brand_id':B[key[0]]['id'],'brand_name':B[key[0]]['name'],'region':key[1],'same_four_fields':same4,'status':status,'reason':'상가ID만으로매장동일성을확정하지않음;주소좌표동일로삭제하지않음','rows':[{'csv_line':x['line'],**x['row']} for x in g],'source_links':['https://give.khu.ac.kr/data/file/data_01/2942980483_4m06iprk_0f2530262072e8695d761bfb5695b2abd396d2ad.pdf'] if verified else [],'different_source_labels':distinct,'search_status':'공식검색색인에서3개지점명확인;PDF직접열기는용량제한' if verified else '개별외부검색미실시또는미확인'})
# This CSV has no repeated bizesId. Still assert conflicts cannot escape the gate.
conflictids=set(P['duplicate_ids'])
for x in items:
 if x['row']['bizesId'] in conflictids:x['reasons'].append('동일상가ID복수행검토필요')
os.makedirs('deliverables',exist_ok=True)
output=[{'id':b['id'],'name':b['name'],'regions':{r:[] for r in regions}} for b in B]
fields=['rdnmAdr','bldNm','bizesId','bizesNm','brchNm','ctprvnNm','signguNm','dongNo','flrNo','hoNo']
accepted=[];pending=[]
for x in items:
 if x['reasons']:pending.append(x);continue
 i=x['brand_index'];r=x['row'];m={k:r[k] for k in fields};m['lat']=x['lat'];m['lon']=x['lon']
 title=r['bizesNm'];branch=r['brchNm']
 if branch and norm(branch) not in norm(title):title+=' '+branch
 m['marker_title']=title
 output[i]['regions'][R[r['ctprvnNm']]].append(m);accepted.append(x)

def dump(name,data):
 with open('deliverables/'+name,'w') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
dump('cafe_map.json',output)
dump('duplicate_review.json',duplicates)
# Preserve full original row in pending data. Candidate IDs are alternatives, not memberships.
dump('pending_review.json',[{'csv_line':x['line'],'candidate_brands':[{'id':B[i]['id'],'name':B[i]['name']} for i in x['candidate_indices']],'reason_codes':x['reasons'],'match_basis':x['basis'],'source_row':x['row']} for x in pending])
with open('deliverables/match_audit.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['csv_line','bizesId','brand_id','brand_name','region','match_basis','status','reasons'])
 for x in items:
  i=x['brand_index'];w.writerow([x['line'],x['row']['bizesId'],B[i]['id'] if i is not None else '',B[i]['name'] if i is not None else '',x['row']['ctprvnNm'],x['basis'],'pending' if x['reasons'] else 'map', '|'.join(x['reasons'])])
with open('deliverables/brand_region_counts.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['id','name',*regions,'total'])
 for b in output:
  ns=[len(b['regions'][r]) for r in regions];w.writerow([b['id'],b['name'],*ns,sum(ns)])
summary={'source_rows':P['total'],'candidate_rows':len(items),'map_rows':len(accepted),'pending_rows':len(pending),'no_candidate_rows':P['total']-len(items),'not_in_map_rows':P['total']-len(accepted),'brand_count':len(B),'brands_with_map_rows':sum(any(b['regions'].values()) for b in output),'source_region_counts':P['regions'],'map_region_counts':{r:sum(len(b['regions'][r]) for b in output) for r in regions},'pending_reason_counts':dict(collections.Counter(r for x in pending for r in x['reasons'])),'duplicate_groups':len(duplicates),'same_four_field_groups':sum(d['same_four_fields'] for d in duplicates),'duplicate_pending_groups':sum(d['status']=='동일매장여부보류' for d in duplicates),'duplicate_kept_distinct_groups':sum(d['status']=='공식목록의서로다른지점명보존' for d in duplicates),'removed_rows':0,'repeated_bizesId_groups':len(conflictids),'coordinate_issue_counts_entire_csv':P['allcoords']}
dump('summary.json',summary)
# Cross-check the file that will be delivered, not only in-memory totals.
O=json.load(open('deliverables/cafe_map.json'))
assert len(O)==842 and [(b['id'],b['name']) for b in O]==[(b['id'],b['name']) for b in B]
assert sum(len(a) for b in O for a in b['regions'].values())==len(accepted)==sum(summary['map_region_counts'].values())
assert P['total']==len(accepted)+len(pending)+summary['no_candidate_rows']
assert len({m['bizesId'] for b in O for a in b['regions'].values() for m in a})==len(accepted)
assert all(type(m['lat']) is float and type(m['lon']) is float for b in O for a in b['regions'].values() for m in a)
print(json.dumps(summary,ensure_ascii=False,indent=2))
with open('pending_priority.txt','w') as f:
 c=collections.defaultdict(list)
 for x in pending:
  if x['brand_index'] is not None:c[x['brand_index']].append(x)
 for i,xs in sorted(c.items(),key=lambda kv:-len(kv[1])):
  f.write(str(i)+' '+str(B[i]['name'])+' '+str(len(xs))+'\n')
  f.write(str(collections.Counter(x['row']['bizesNm'] for x in xs).most_common(12))+'\n')
