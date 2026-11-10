from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from .models import Brand
REGIONS = ['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주']

def serialize(b):
    return {'id':b.slug,'name':b.name,'category':b.category,'tagline':b.tagline,'english_name':b.english_name,'description':b.description,'image':b.image,'color':b.color,'initial_cost_krw':b.initial_cost_krw,'costs':b.costs,'area_sqm':b.area_sqm,'stats':[{'year':s.year,'stores':s.stores,'opened':s.opened,'closed':s.closed,'annual_sales_krw':s.annual_sales_krw,'source_label':s.source_label,'source_url':s.source_url,'regions':{r.region:r.stores for r in s.regional_stats.all()}} for s in b.annual_stats.all()]}

@require_GET
def brand_list(request):
    # 실데이터가 생기면 데모 브랜드를 자동 제외해 혼합 통계를 방지합니다.
    qs = Brand.objects.all()
    if qs.filter(is_demo=False).exists(): qs=qs.filter(is_demo=False)
    brands=list(qs.prefetch_related('annual_stats__regional_stats').order_by('id'))
    stats=[s for b in brands for s in b.annual_stats.all()]
    sources=sorted(set(s.source_label for s in stats))
    return JsonResponse({'schema_version':'1.0','is_demo':all(b.is_demo for b in brands),'source_label':' / '.join(sources) or '데이터 없음','updated_at':str(max((s.updated_at for s in stats),default='')),'years':sorted({s.year for s in stats},reverse=True),'regions':REGIONS,'brands':[serialize(b) for b in brands]},json_dumps_params={'ensure_ascii':False})

@require_GET
def brand_detail(request,slug):
    return JsonResponse(serialize(get_object_or_404(Brand.objects.prefetch_related('annual_stats__regional_stats'),slug=slug)),json_dumps_params={'ensure_ascii':False})
