"""Site search assistant: deterministic retrieval and grounded snippets, no external AI."""
import re
from django.db.models import Q
from .models import FAQ

PAGES=[
 ('브랜드 탐색','Brands','/brands/blist/','브랜드 업종 검색 매출 개업 폐업 창업비용 brand search sales costs'),
 ('지역상권분석','Regions','/brands/bregion/','시 군 구 동 지도 경쟁 분포 매장 지역 map location district competition'),
 ('브랜드 비교','Compare brands','/brands/bcompare/','비교 체크박스 비교함 compare checkbox'),
 ('회수 계산기','Payback calculator','/brands/calculator/','투자 회수 손익분기 변동비 월세 인건비 calculator payback investment bep'),
 ('점주 커뮤니티','Owner community','/community/','글 댓글 수정 삭제 점주 커뮤니티 게시판 community post comment edit delete'),
 ('점주 인증','Owner verification','/community/verify/','점주 인증 계약서 사업자 서류 검토 verification owner document'),
 ('양도양수','Transfer market','/market/transfer/','양도 양수 권리금 보증금 월세 매물 transfer listing premium rent'),
 ('본사 입점','Partner center','/partners/pricing/','본사 파트너 입점 요금 광고 partner headquarters pricing'),
 ('고객센터','Help center','/help/','고객센터 문의 도움말 support help contact'),
 ('데이터 안내','Data guide','/brands/guide/','데이터 출처 기준 공시 data source year'),
]


def tokenize(text):
    tokens=re.findall(r'[가-힣a-z0-9]+',text.lower())
    result=set(tokens)
    for token in tokens:
        if re.search('[가-힣]',token):
            for suffix in ('하는법','어떻게','해주세요','하나요','인가요','하려면','에서','으로','하기','좀','은','는','이','가','을','를'):
                if token.endswith(suffix) and len(token)>len(suffix)+1:result.add(token[:-len(suffix)])
    return {t for t in result if len(t)>1}


def respond(question,user,language='ko',current_path=''):
    english=language=='en';tokens=tokenize(question)
    # Brand facts are taken from the DB; protected figures require the same sign-in as detail pages.
    from brands.views import visible_brands,with_stats
    brands=visible_brands().none()
    for token in sorted(tokens,key=len,reverse=True):
        brands=visible_brands().filter(name__icontains=token)
        if brands.exists():break
    found=list(with_stats(brands)[:3])
    if found:
        lines=[];links=[]
        for brand in found:
            text=f'{brand.name} · {brand.category}'
            if user.is_authenticated:
                annual=brand.annual_stats.order_by('-year').first()
                if annual:
                    text+=f' · {annual.year}'
                    if annual.stores is not None:text+=f' · {annual.stores:,} '+('stores' if english else '개 매장')
                    if annual.annual_sales_krw is not None:text+=f' · '+('average monthly sales: ' if english else '평균 월매출: ')+f'{round(annual.annual_sales_krw/12/10000):,} '+('× KRW 10,000' if english else '만원')
            lines.append(text);links.append({'title':brand.name,'url':f'/brands/bview/{brand.slug}/'})
        return {'answer':'\n'.join(lines)+('' if user.is_authenticated else ('\nSign in to view detailed brand statistics.' if english else '\n브랜드별 상세 통계는 로그인 후 확인할 수 있습니다.')),'sources':links,'mode':'local_search'}
    faqs=list(FAQ.objects.filter(is_published=True))
    ranked=[]
    for faq in faqs:
        keywords=' '.join(p[3] for p in PAGES if p[2]==faq.link)
        title=faq.question+' '+faq.question_en+' '+keywords
        score=sum((4 if t in title.lower() else 1 if t in (faq.answer+' '+faq.answer_en).lower() else 0) for t in tokens)
        if score and faq.link and current_path.startswith(faq.link):score+=1
        ranked.append((score,faq))
    ranked.sort(key=lambda pair:pair[0],reverse=True)
    if ranked and ranked[0][0]>0:
        faq=ranked[0][1]
        answer=faq.answer_en if english and faq.answer_en else faq.answer
        links=[{'title':faq.question_en if english and faq.question_en else faq.question,'url':'/help/?query='+__import__('urllib.parse',fromlist=['quote']).quote(faq.question)}]
        if faq.link.startswith('/') and not faq.link.startswith('//'):links.insert(0,{'title':'Open related page' if english else '관련 페이지 열기','url':faq.link})
        return {'answer':answer,'sources':links,'mode':'local_search'}
    page_links=sorted(PAGES,key=lambda p:sum(t in p[3] for t in tokens),reverse=True)[:3]
    return {'answer':('I can help you find site features and registered brand data. Try “compare”, “owner verification”, “payback” or a brand name.' if english else '사이트 기능과 등록된 브랜드 정보를 찾아드릴 수 있어요. “비교하는 방법”, “점주 인증”, “회수 계산”, 브랜드명처럼 구체적으로 물어보세요. 확인되지 않은 매출이나 서류 진위는 답변하지 않습니다.'),
            'sources':[{'title':p[1] if english else p[0],'url':p[2]} for p in page_links],'mode':'local_search'}
