import csv,io,json,zipfile,pathlib,collections,re,unicodedata,html,math,hashlib
OUT=pathlib.Path('remaining_output');OUT.mkdir(exist_ok=True);(OUT/'maps').mkdir(exist_ok=True)
def norm(s):
 s=unicodedata.normalize('NFKD',html.unescape(s or '')).casefold()
 return ''.join(c for c in unicodedata.normalize('NFC',''.join(c for c in s if not unicodedata.combining(c))) if c.isalnum())
def variants(s):
 s=s or '';v={s,re.sub(r'\([^)]*\)','',s)}
 for p in re.findall(r'\(([^)]*)\)',s):v.add(p+s[s.rfind(')')+1:])
 return v
Z=zipfile.ZipFile('upload/brands_by_category(1).zip');B=[];cats={};A=collections.defaultdict(dict)
def add(s,i,k):
 a=norm(s)
 if len(a)>=2:A[a].setdefault(i,set()).add(k)
for n in Z.namelist():
 bs=json.loads(Z.read(n));cat=n[:-5];cats[cat]=[]
 for b in bs:
  i=len(B);B.append({**b,'category':cat});cats[cat].append(i)
  for v in variants(b['name']):add(v,i,'catalog')
  if b.get('english_name'):add(b['english_name'],i,'catalog')
  for h in b.get('history',[])+[{'name':x} for x in b.get('name_variants',[])]:
   for v in variants(h.get('name')):add(v,i,'history')
  for v in variants(b['name']):
   a=norm(v)
   for t in ['헤어','영어','학원','어학원','피씨방','pc방','안경','호텔','모텔','스터디카페','세탁소','세탁','피트니스']:
    if a.endswith(t) and len(a[:-len(t)])>=3:add(a[:-len(t)],i,'short_candidate')
# Explicit, source-reviewed phonetic spellings, never new brand IDs.
manual={'GS25':['지에스25','지에스이십오'],'GS THE FRESH':['GS더프레시','지에스더프레시'],'CU':['씨유'],'씨유(CU)':['씨유','CU'],'이마트24':['emart24']}
for i,b in enumerate(B):
 for v in manual.get(b['name'],[]):add(v,i,'reviewed_alias')
T={}
for a in A:
 t=T
 for c in a:t=t.setdefault(c,{})
 t['$']=a
def hits(s):
 out=[]
 for p in range(len(s)):
  t=T
  for q in range(p,len(s)):
   if s[q] not in t:break
   t=t[s[q]]
   if '$' in t:out.append((p,q+1,t['$']))
 return out
allowed={
'교육서비스업':set(['교육_(교과)','교육_(외국어)','기타_교육','기타_서비스','유아관련','유아_관련_(교육_외)','스포츠_관련']),
'수리개인서비스업':set(['미용실','세탁','자동차_관련','기타_서비스','반려동물_관련']),
'소매업':set(['편의점','종합소매점','기타도소매','농수산물','(건강)식품','안경','약국','의류_패션','화장품','반려동물_관련','자동차_관련','기타_서비스']),
'숙박업':set(['숙박','기타_서비스']),
'예술스포츠여가서비스업':set(['PC방','오락','스포츠_관련','유아관련','유아_관련_(교육_외)','기타_서비스','임대','기타_교육'])}
R={'서울특별시':'서울','부산광역시':'부산','대구광역시':'대구','인천광역시':'인천','대전광역시':'대전','울산광역시':'울산','세종특별자치시':'세종','경기도':'경기','강원특별자치도':'강원','충청북도':'충북','충청남도':'충남','전북특별자치도':'전북','경상북도':'경북','경상남도':'경남','제주특별자치도':'제주','전남광주통합특별시':'전남광주통합특별시'}
regions=['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원','충북','충남','전북','전남','경북','경남','제주','전남광주통합특별시']
safe3=set('씨유 CU 미샤 더샘 GS25 KGB 올리브영 아트박스 다비치 크린토피아'.lower().split())
generic=set('리안 블루클럽 토리헤어 리챠드 헤어팰리스 헤어스토리 헤어아트 헤어카페 호텔모두 호텔더휴 대한호텔 해법영어 눈높이 재능교육 공부방 휴게소 시선 플랜 데니스 정글비 온누리 메디팜'.split())
# These generic/proper-name choices are conservative; source lookup can promote individual rows later.
C=[];stats={};idseen={};idconflicts=set();source_meta=[]
audit=open(OUT/'row_disposition_initial.csv','w',encoding='utf-8-sig',newline='');w=csv.writer(audit);w.writerow(['source','csv_record','bizesId','ctprvnNm','candidate_index'])
for sector in allowed:
 path=pathlib.Path('upload')/('전국상가정보_'+sector+'_202610.zip');z=zipfile.ZipFile(path);member=next(n for n in z.namelist() if n.endswith('records.csv'))
 ss=collections.Counter();source_reg=collections.Counter();digest=hashlib.sha256()
 with z.open(member) as raw:
  for chunk in iter(lambda:raw.read(1048576),b''):digest.update(chunk)
 source_meta.append({'source':path.name,'member':member,'csv_sha256':digest.hexdigest(),'bytes':z.getinfo(member).file_size,'manifest':json.loads(z.read(next(n for n in z.namelist() if n.endswith('manifest.json'))))})
 for line,r in enumerate(csv.DictReader(io.TextIOWrapper(z.open(member),encoding='utf-8-sig')),2):
  ss['source_rows']+=1;source_reg[r['ctprvnNm']]+=1
  ident=r['bizesId']
  if ident in idseen:idconflicts.add(ident)
  else:idseen[ident]=(sector,line)
  try:
   lat=float(r['lat']);lon=float(r['lon'])
   issue=not(math.isfinite(lat) and math.isfinite(lon) and -90<=lat<=90 and -180<=lon<=180)
   if issue:ss['coordinate_invalid']+=1
   elif not(32<=lat<=39.5 and 124<=lon<=132):ss['coordinate_outside_screen']+=1;issue=True
  except ValueError:lat=lon=None;issue=True;ss['coordinate_missing_nonnumeric']+=1
  s=norm(r['bizesNm']);hh=hits(s);ci=''
  if hh:
   ci=len(C);ss['candidate_rows']+=1;strong=[]
   for p,q,a in hh:
    if p:continue
    tail=s[q:];shape=''
    if not tail:shape='whole_name'
    elif tail in ['학원','어학원','헤어','헤어살롱','pc방','피씨방','안경원','호텔','모텔','편의점']:shape='name_with_business_type'
    elif tail.endswith(('점','지사','센터','캠퍼스','학원','교습소','공부방')) and len(tail)<=25:shape='branch_form'
    else:
     toks=[]
     for k in ['ctprvnNm','signguNm','adongNm','ldongNm','bldNm','brchNm']:
      for tok in r[k].split():
       n=norm(tok);toks.append(n);toks.append(re.sub('(특별자치시|특별자치도|특별시|광역시|[시군구동읍면리])$','',n))
     if any(len(t)>=2 and tail.startswith(t) for t in toks):shape='source_location_hint'
    if shape:
     for i,ks in A[a].items():
      if ks.intersection(['catalog','reviewed_alias']):strong.append((q-p,i,a,shape))
   choices=[];chosen=None;basis='';reasons=[]
   if strong:
    m=max(t[0] for t in strong);strong=[t for t in strong if t[0]==m];choices=sorted({t[1] for t in strong})
   if len(choices)==1:
    chosen=choices[0];v=next(t for t in strong if t[1]==chosen);basis=v[3];a=v[2];b=B[chosen]
    if (len(a)<=3 and a not in safe3) or norm(re.sub(r'\([^)]*\)','',b['name'] or '')) in generic:reasons.append('short_or_generic_name')
    if b['category'] not in allowed[sector]:reasons.append('cross_sector_review')
    tail=s[len(a):]
    if any(tail.startswith(t) for t in ['공장','본사','물류','익스프레스']):reasons.append('subbrand_or_facility')
   elif len(choices)>1:reasons.append('multiple_brand_ids')
   else:reasons.append('substring_historical_or_unverified_alias')
   if not choices:choices=sorted({i for p,q,a in hh for i in A[a]})
   if issue:reasons.append('coordinate_issue')
   if not r['rdnmAdr']:reasons.append('missing_road_address')
   if r['ctprvnNm'] not in R:reasons.append('unmapped_region')
   if any(c in r['bizesNm'] for c in ['&','＆',',','，']) and chosen is not None and s!=norm(B[chosen]['name']):reasons.append('compound_name_review')
   C.append({'source':sector,'csv_record':line,'row':r,'brand_index':chosen,'candidate_indices':choices,'basis':basis,'reasons':reasons,'lat':lat,'lon':lon})
  w.writerow([sector,line,ident,r['ctprvnNm'],ci])
 stats[sector]={'counts':dict(ss),'source_regions':dict(source_reg)}
 print(sector,dict(ss),flush=True)
audit.close()
# No automatic deletions, even identical IDs. Preserve conflicting occurrences in pending.
for x in C:
 if x['row']['bizesId'] in idconflicts:x['reasons'].append('repeated_bizesId_preserve_all')
groups=collections.defaultdict(list)
for x in C:
 if x['brand_index'] is not None:groups[(x['brand_index'],x['row']['ctprvnNm'],norm(x['row']['rdnmAdr']))].append(x)
dups=[]
for k,g in groups.items():
 if len(g)<2:continue
 for x in g:x['reasons'].append('same_brand_address_store_identity_unresolved')
 dups.append({'group_id':'D'+str(len(dups)+1).zfill(6),'brand_id':B[k[0]]['id'],'brand_name':B[k[0]]['name'],'category':B[k[0]]['category'],'same_four_fields':len({tuple(x['row'][t] for t in ['rdnmAdr','bldNm','lat','lon']) for x in g})==1,'status':'pending_no_merge','source_links':[],'rows':[{'source':x['source'],'csv_record':x['csv_record'],**x['row']} for x in g]})
# Every category and every catalog brand retained; files describe only the five new sources.
O=[{'id':b['id'],'name':b['name'],'regions':{r:[] for r in regions}} for b in B];reasons=collections.Counter();counts=collections.Counter();bycat=collections.Counter();fields=['rdnmAdr','bldNm','bizesId','bizesNm','brchNm','ctprvnNm','signguNm','dongNo','flrNo','hoNo'];pending=0
with open(OUT/'pending_review.jsonl','w') as f,open(OUT/'match_audit.csv','w',encoding='utf-8-sig',newline='') as af:
 aw=csv.writer(af);aw.writerow(['source','csv_record','bizesId','category','brand_id','status','match_basis','reasons'])
 for x in C:
  i=x['brand_index'];b=B[i] if i is not None else None;r=x['row'];status='pending' if x['reasons'] else 'map';counts[status]+=1;stats[x['source']]['counts'][status]=stats[x['source']]['counts'].get(status,0)+1
  if x['reasons']:
   pending+=1;reasons.update(set(x['reasons']));f.write(json.dumps({'source':x['source'],'csv_record':x['csv_record'],'candidate_brands':[{'id':B[j]['id'],'name':B[j]['name'],'category':B[j]['category']} for j in x['candidate_indices']],'match_basis':x['basis'],'reasons':x['reasons'],'search_status':'not_individually_verified','source_row':r},ensure_ascii=False,allow_nan=False)+'\n')
  else:
   m={k:r[k] for k in fields};m.update(lat=x['lat'],lon=x['lon']);m['marker_title']=r['bizesNm']+(' '+r['brchNm'] if r['brchNm'] and norm(r['brchNm']) not in norm(r['bizesNm']) else '');O[i]['regions'][R[r['ctprvnNm']]].append(m);bycat[b['category']]+=1
  aw.writerow([x['source'],x['csv_record'],r['bizesId'],b['category'] if b else '',b['id'] if b else '',status,x['basis'],'|'.join(x['reasons'])])
# Final full row ledger uses the final duplicate and ID decisions.
with open(OUT/'row_disposition.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['source','csv_record','bizesId','ctprvnNm','status'])
 for r in csv.DictReader(open(OUT/'row_disposition_initial.csv',encoding='utf-8-sig')):
  ci=r['candidate_index'];st=('pending' if C[int(ci)]['reasons'] else 'map') if ci else 'no_candidate';w.writerow([r['source'],r['csv_record'],r['bizesId'],r['ctprvnNm'],st])
(OUT/'row_disposition_initial.csv').unlink()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False))
for cat,ii in cats.items():dump(OUT/'maps'/(cat+'.json'),[O[i] for i in ii])
dump(OUT/'duplicate_review.json',dups);dump(OUT/'source_manifest.json',source_meta)
with open(OUT/'brand_region_counts.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['category','id','name',*regions,'total'])
 for i,b in enumerate(B):ns=[len(O[i]['regions'][r]) for r in regions];w.writerow([b['category'],b['id'],b['name'],*ns,sum(ns)])
with open(OUT/'duplicate_removals.csv','w',encoding='utf-8-sig',newline='') as f:csv.writer(f).writerow(['kept_source_record','removed_source_record','reason'])
with open(OUT/'aliases.csv','w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['normalized_alias','brand_id','category','origin'])
 for a,js in A.items():
  for i,ks in js.items():w.writerow([a,B[i]['id'],B[i]['category'],'|'.join(sorted(ks))])
for cat,ii in cats.items():
 data=json.loads((OUT/'maps'/(cat+'.json')).read_text());assert [(b['id'],b['name']) for b in data]==[(B[i]['id'],B[i]['name']) for i in ii]
 assert sum(len(ms) for b in data for ms in b['regions'].values())==bycat[cat]
assert sum(bycat.values())==counts['map']
for sec,ss in stats.items():ss['counts']['no_candidate']=ss['counts']['source_rows']-ss['counts'].get('candidate_rows',0);assert ss['counts']['source_rows']==ss['counts'].get('map',0)+ss['counts'].get('pending',0)+ss['counts']['no_candidate']
S={'sources':stats,'category_count':len(cats),'brand_count':len(B),'brands_with_map_rows':sum(any(b['regions'].values()) for b in O),'map_rows':counts['map'],'pending_rows':pending,'pending_with_link_basis':sum(bool(x['basis']) for x in C if x['reasons']),'source_rows':sum(ss['counts']['source_rows'] for ss in stats.values()),'category_map_counts':dict(bycat),'pending_reasons_nonexclusive':dict(reasons),'duplicate_groups':len(dups),'same_four_field_groups':sum(d['same_four_fields'] for d in dups),'repeated_bizesId_count':len(idconflicts),'removed_rows':0,'validation':{'all_category_json_parse':'PASS','all_catalog_id_name_order_preserved':'PASS','category_region_totals':'PASS','source_disposition_totals':'PASS'},'limitations':['name_based_not_verified_franchise_or_live_status','no_full_address_coordinate_geocoding','pending_not_all_individually_web_searched','only_five_new_source_archives_no_previous_cafe_results_merged']}
dump(OUT/'summary.json',S)
print(json.dumps(S,ensure_ascii=False,indent=2),flush=True)
