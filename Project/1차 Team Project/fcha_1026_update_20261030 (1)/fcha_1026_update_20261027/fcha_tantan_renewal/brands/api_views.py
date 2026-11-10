from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator
from django.db.models import Max
from .models import AnnualStat, Brand
REGIONS = ['서울','경기','인천','부산','대구','광주','대전','울산','세종','강원','충북','충남','전북','전남','경북','경남','제주']

def serialize(b, detailed=True):
    data = {'id':b.slug,'name':b.name,'category':b.category,'tagline':b.tagline,'english_name':b.english_name,'description':b.description,'image':b.image,'color':b.color,'initial_cost_krw':b.initial_cost_krw,'costs':b.costs,'area_sqm':b.area_sqm,'stats':[{'year':s.year,'stores':s.stores,'opened':s.opened,'closed':s.closed,'annual_sales_krw':s.annual_sales_krw,'source_label':s.source_label,'source_url':s.source_url,'regions':{r.region:r.stores for r in s.regional_stats.all()}} for s in b.annual_stats.all()]}

    if not detailed:
        for key in ('description','initial_cost_krw','costs','area_sqm'): data.pop(key, None)
        for stat in data['stats']:
            stat.pop('regions', None)
            stat.pop('source_url', None)
    else:
        from .models import AreaSales
        area = {a.annual_stat_id: a for a in AreaSales.objects.filter(annual_stat__brand=b)}
        for stat, record in zip(data['stats'], b.annual_stats.all()):
            value = area.get(record.id)
            stat['annual_sales_per_pyeong_krw'] = value.annual_sales_per_pyeong_krw if value else None
            stat['area_source_label'] = value.source_label if value else ''
    return data

@require_GET
def brand_list(request):
    # 실데이터가 생기면 데모 브랜드를 자동 제외해 혼합 통계를 방지합니다.
    qs = Brand.objects.all()
    if qs.filter(is_demo=False).exists(): qs=qs.filter(is_demo=False)
    # 브랜드가 1만 개가 넘어 한 번에 100개씩 나눠 보냅니다(?page=2).
    page=Paginator(qs.order_by('id'),100).get_page(request.GET.get('page'))
    brands=list(qs.filter(pk__in=[b.pk for b in page.object_list]).prefetch_related('annual_stats__regional_stats').order_by('id'))
    stats=AnnualStat.objects.filter(brand__in=qs)
    sources=sorted(set(stats.values_list('source_label',flat=True)))
    return JsonResponse({'schema_version':'1.1','is_demo':not qs.filter(is_demo=False).exists(),'source_label':' / '.join(sources) or '데이터 없음','updated_at':str(stats.aggregate(m=Max('updated_at'))['m'] or ''),'years':sorted(set(stats.values_list('year',flat=True)),reverse=True),'regions':REGIONS,
                         'page':page.number,'num_pages':page.paginator.num_pages,'count':page.paginator.count,
                         'brands':[serialize(b, detailed=request.user.is_authenticated) for b in brands]},json_dumps_params={'ensure_ascii':False})

@require_GET
def brand_detail(request,slug):
    if not request.user.is_authenticated: return JsonResponse({'detail':'로그인이 필요합니다.'}, status=401)
    return JsonResponse(serialize(get_object_or_404(Brand.objects.prefetch_related('annual_stats__regional_stats'),slug=slug)),json_dumps_params={'ensure_ascii':False})
