import urllib.request,urllib.parse,http.cookiejar,re,json,concurrent.futures,sys,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scrape import TableParser

root=Path('research/primary');root.mkdir(exist_ok=True)
brands={'CU':'씨유','GS25':'GS25','세븐일레븐':'세븐일레븐','이마트24':'이마트24','메가커피':'메가엠지씨','컴포즈커피':'컴포즈커피','이디야커피':'이디야커피','빽다방':'빽다방','투썸플레이스':'투썸플레이스','교촌치킨':'교촌치킨','BHC':'비에이치씨','굽네치킨':'굽네치킨','비비큐(BBQ)':'비비큐','처갓집양념치킨':'처갓집양념치킨','에이바헤어':'에이바헤어','블루클럽':'블루클럽','제오헤어':'제오헤어','로이드밤':'로이드밤','토리헤어':'토리헤어'}

def tables(s):
 out=[]
 for item in re.findall(r'<table\b[\s\S]*?</table>',s,re.I):
  p=TableParser();p.feed(item)
  cap=re.search(r'<caption[^>]*>([\s\S]*?)</caption>',item,re.I)
  if p.tables:out.append({'caption':re.sub('<[^>]+>','',cap.group(1)).strip() if cap else '',**p.tables[0]})
 return out

def fetch(pair):
 brand,search=pair
 try:
  op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));op.addheaders=[('User-Agent','Mozilla/5.0')]
  listurl='https://franchise.ftc.go.kr/mnu/00013/program/userRqst/list.do?column=brd&searchKeyword='+urllib.parse.quote(search)
  raw=op.open(listurl,timeout=30).read().decode()
  links=re.findall(r"fn_moveUrl\('/mnu/00013/program/userRqst/view.do\?encFirMstSn=', '([^']+)'\)\">([^<]+)</a>",raw)
  candidates=[(token,html.unescape(label)) for token,label in links if search.lower() in html.unescape(label).lower()]
  if brand=='이마트24':candidates=[p for p in candidates if p[1]=='이마트24(emart24)']
  if brand=='CU':candidates=[p for p in candidates if p[1]=='씨유(CU)']
  expected={'BHC':'비에이치씨(BHC)','메가커피':'메가엠지씨커피(MEGA MGC COFFEE)','컴포즈커피':'컴포즈커피(COMPOSE COFFEE)','제오헤어':'XEO HAIR(제오헤어)','비비큐(BBQ)':'비비큐(BBQ)'}.get(brand,brand)
  if brand not in ('CU','이마트24'):
   exact=[p for p in candidates if p[1].replace(' ','').lower()==expected.replace(' ','').lower()]
   if exact:candidates=exact
  if not candidates:raise ValueError('해당 브랜드 링크 없음')
  token,label=candidates[0]
  view='https://franchise.ftc.go.kr/mnu/00013/program/userRqst/view.do?encFirMstSn='+urllib.parse.quote(token,safe='')
  page=op.open(urllib.request.Request(view,headers={'Referer':listurl}),timeout=45).read().decode()
  if '가맹점사업자의 평균 매출액' not in page:
   (root/(brand+'_error.html')).write_text(page,encoding='utf-8')
   raise ValueError('상세 페이지 오류 '+view)
  versions=re.findall(r'<option\s+value="([^"]+)"[^>]*>([^<]+)</option>',page)
  versions=[(tok,html.unescape(lbl)) for tok,lbl in versions if re.search(r'\(20\d\d\.\d\d\.\d\d\)',lbl)]
  result={'brand':brand,'label':label,'list_url':listurl,'latest_url':view,'retrieved_date':'2026-10-22','latest_tables':tables(page),'versions':versions}
  old=[(tok,lbl) for tok,lbl in versions if '(2025.' in lbl]
  if old:
   tok,lbl=old[0];u='https://franchise.ftc.go.kr/mnu/00013/program/userRqst/view.do?encFirMstSn='+urllib.parse.quote(tok,safe='')
   p=op.open(urllib.request.Request(u,headers={'Referer':view}),timeout=45).read().decode()
   result['disclosure_2025_url']=u;result['disclosure_2025_label']=lbl;result['disclosure_2025_tables']=tables(p)
  (root/(brand+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
  return (brand,'OK',len(result['latest_tables']),result.get('disclosure_2025_label'))
 except Exception as e:return (brand,'ERROR',str(e))

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
  for result in ex.map(fetch,brands.items()):print(result,flush=True)
