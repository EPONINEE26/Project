import csv,io,json,zipfile,re,unicodedata,collections,hashlib
B=json.load(open('cafe_source.json'))
def norm(s):
 import html
 s=unicodedata.normalize('NFKD',html.unescape(s or '')).casefold()
 s=''.join(c for c in s if not unicodedata.combining(c))
 return ''.join(c for c in unicodedata.normalize('NFC',s) if c.isalnum())
A=collections.defaultdict(list)
def add(s,i,kind):
 a=norm(s)
 if len(a)>=2 and (i,kind) not in A[a]:A[a].append((i,kind))
def variants(s):
 s=s or ''; out=[s]
 if '(' in s:
  outer=re.sub(r'\([^)]*\)','',s);out.append(outer)
  for p in re.findall(r'\(([^)]*)\)',s):
   suffix=s[s.rfind(')')+1:];out.append(p+suffix)
 return set(out)
for i,b in enumerate(B):
 for s in variants(b['name']):add(s,i,'catalog')
 if b.get('english_name'):add(b['english_name'],i,'english')
 for h in b.get('history',[])+[{'name':n} for n in b.get('name_variants',[])]:
  for s in variants(h.get('name')):
   add(s,i,'history')
 for s in variants(b['name']):
  ns=norm(s)
  for token in ['커피','카페','coffee','cafe','스페셜티커피']:
   if ns.endswith(token) and len(ns[:-len(token)])>=2:add(ns[:-len(token)],i,'short_candidate')
   if ns.startswith(token) and len(ns[len(token):])>=2:add(ns[len(token):],i,'short_candidate')
manual={238:['메가커피','메가MGC커피','메가엠지씨커피','megacoffee'],545:['이디야','EDIYA'],819:['할리스커피','HOLLYS','HOLLYSCOFFEE'],747:['탐앤탐스','TOMNTOMS'],755:['텐퍼센트커피','텐퍼센트','TENPERCENTCOFFEE'],232:['매머드커피익스프레스','매머드익스프레스','메머드익스프레스'],233:['메머드커피'],116:['달콤커피','달콤'],526:['우주라이크커피'],531:['원유로커피'],69:['감성커피'],133:['THEVENTI'],352:['PAIKSCOFFEE'],762:['투썸','ATWOSOMEPLACE'],773:['PASCUCCI'],475:['엔젤리너스'],371:['셀렉토'],271:['카페베네','CAFFEBENE'],64:['프라우송'],336:['비맨션커피토스트'],99:['꿀스커피'],787:['포트캔커피'],267:['바다씨씨엠커피']}
for i,ss in manual.items():
 for s in ss:add(s,i,'manual_candidate')
trie={}
for a in A:
 t=trie
 for c in a:t=t.setdefault(c,{})
 t['$']=a

def hits(s):
 found=[]
 for p in range(len(s)):
  t=trie
  for q in range(p,len(s)):
   if s[q] not in t:break
   t=t[s[q]]
   if '$' in t:found.append((p,q+1,t['$']))
 return found
rows=[]; counts=collections.Counter(); regions=collections.Counter(); ids=collections.defaultdict(list); exact=collections.Counter(); allcoords=collections.Counter()
with zipfile.ZipFile('upload/records.zip') as z:
 for line,r in enumerate(csv.DictReader(io.TextIOWrapper(z.open('records.csv'),encoding='utf-8-sig')),2):
  counts['total']+=1;regions[r['ctprvnNm']]+=1
  digest=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
  ids[r['bizesId']].append((line,digest))
  try:
   lat=float(r['lat']);lon=float(r['lon'])
   if not (-90<=lat<=90 and -180<=lon<=180):allcoords['invalid_range']+=1
   elif not (32<=lat<=39.5 and 124<=lon<=132):allcoords['outside_korea_screen']+=1
  except ValueError:allcoords['missing_or_nonnumeric']+=1
  h=hits(norm(r['bizesNm']))
  if h:rows.append({'line':line,'row':r,'hits':h})
print('total',counts,'regions',regions,'coords',allcoords,'candidates',len(rows),'duplicate_ids',sum(len(v)>1 for v in ids.values()))
json.dump({'brands':B,'aliases':A,'rows':rows,'total':counts['total'],'regions':regions,'allcoords':allcoords,'duplicate_ids':{k:v for k,v in ids.items() if len(v)>1}},open('profile.json','w'),ensure_ascii=False)
by=collections.defaultdict(collections.Counter)
for item in rows:
 for i in set(i for p,q,a in item['hits'] for i,k in A[a]):by[i][item['row']['bizesNm']]+=1
with open('candidate_names.txt','w') as f:
 for i in sorted(by):
  f.write('\n'+str(i)+' '+str(B[i]['name'])+' '+str(sum(by[i].values()))+'\n')
  f.write(str(by[i].most_common(18))+'\n')
print('saved profile')
