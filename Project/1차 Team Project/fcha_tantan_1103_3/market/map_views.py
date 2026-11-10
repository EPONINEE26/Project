from django.contrib.auth.decorators import login_required
import math
from datetime import date
from django.db.models import Count, FloatField, Max, Q
from django.db.models.functions import Cast
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .maps import public_stores,filtered_stores
from .analysis_models import PublicStore, IndustryCode
from .industry_mapping import category_filter


def circle_filter(request):
    keys = ('lat', 'lng', 'radius')
    if not any(key in request.GET for key in keys):
        return None
    lat, lng, radius = (float(request.GET[key]) for key in keys)
    if not all(math.isfinite(v) for v in (lat, lng, radius)) or not (-90 <= lat <= 90 and -180 <= lng <= 180) or radius not in (300, 500, 1000):
        raise ValueError('잘못된 위치 또는 반경')
    return lat, lng, radius


def in_circle(lat, lng, circle):
    if circle is None:
        return True
    center_lat, center_lng, radius = circle
    dy = math.radians(lat - center_lat)
    dx = math.radians(lng - center_lng)
    a = math.sin(dy / 2) ** 2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(lat)) * math.sin(dx / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(a))) <= radius


@login_required
@require_GET
def public_locations(request):
    """지도 범위의 공공 상가 스냅샷. 원본 정밀 좌표는 DB에서 보존합니다."""
    try:
        circle = circle_filter(request)
        west, south, east, north = [float(request.GET[key]) for key in ('west', 'south', 'east', 'north')]
        if not all(math.isfinite(v) for v in (west, south, east, north)):
            raise ValueError()
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError()
        if east - west > 1 or north - south > 1:
            return JsonResponse({'error': '지도를 확대해서 조회해주세요.'}, status=400)
        industry = request.GET.get('industry', '')
        if industry and (not industry.isascii() or not industry.isdigit()):
            raise ValueError()
        if industry and (len(industry) > 19 or int(industry) > 9223372036854775807):
            raise ValueError()
        reference = request.GET.get('reference_on')
        reference = date.fromisoformat(reference) if reference else PublicStore.objects.aggregate(latest=Max('reference_on'))['latest']
    except (ValueError, KeyError, OverflowError):
        return JsonResponse({'error': '지도 범위·업종·날짜를 확인해주세요.'}, status=400)
    qs = PublicStore.objects.filter(reference_on=reference).annotate(
        map_lat=Cast('latitude', FloatField()), map_lng=Cast('longitude', FloatField()),
    ).filter(map_lat__gte=south, map_lat__lte=north, map_lng__gte=west, map_lng__lte=east)
    category = request.GET.get('category', '').strip()
    predicate, mapping_status = category_filter(category)
    qs = qs.filter(predicate)
    if mapping_status == 'unmapped' and IndustryCode.objects.filter(brand_category=category, verified=True).exists():
        mapping_status = 'verified'
    if industry:
        qs = qs.filter(industry_id=int(industry))
    keyword = request.GET.get('query', '').strip()[:100]
    if keyword:
        qs = qs.filter(Q(name__icontains=keyword) | Q(industry__name__icontains=keyword))
    candidates = qs.select_related('industry').defer('raw').order_by('id')
    if circle:
        # 반경 밖 후보를 먼저 제외한 뒤 표시 제한을 적용합니다.
        rows = (row for row in candidates.iterator(chunk_size=1000) if in_circle(float(row.latitude), float(row.longitude), circle))
        selected, total = [], 0
        for row in rows:
            total += 1
            if len(selected) < 500:
                selected.append(row)
    else:
        total, selected = qs.count(), candidates[:500]
    points = [
        {'id': row.pk, 'name': row.name, 'address': row.address,
         'lat': float(row.latitude), 'lng': float(row.longitude),
         'industry': row.industry.name if row.industry else '', 'postcode': row.postcode}
        for row in selected
    ]
    return JsonResponse({
        'points': points, 'total': total, 'limit': 500, 'truncated': total > 500,
        'reference_on': reference.isoformat() if reference else None,
        'source': 'public_store_snapshot',
        'category': category, 'category_mapping': mapping_status,
        'note': '서울 상가 프로젝트 취합본 · 날짜는 프로젝트 스냅샷이며 현재 영업 여부를 보장하지 않습니다.',
    }, json_dumps_params={'ensure_ascii': False})


@login_required
@require_GET
def public_industries(request):
    rows = IndustryCode.objects.filter(publicstore__isnull=False).values('id', 'code', 'name').distinct().order_by('name', 'id')
    return JsonResponse({'industries': list(rows)}, json_dumps_params={'ensure_ascii': False})

@login_required
@require_GET
def locations(request):
    try:
        circle = circle_filter(request)
    except (ValueError, KeyError, OverflowError):
        return JsonResponse({'error': '위치와 반경을 확인해주세요.'}, status=400)
    qs=filtered_stores(request)
    located=qs.exclude(latitude=None).exclude(longitude=None)
    if circle:
        located = [s for s in located if in_circle(float(s.latitude), float(s.longitude), circle)]
    points=[{'id':s.pk,'name':s.brand.name,'brand':s.brand.name,'lat':float(s.latitude),'lng':float(s.longitude),'area':f'{s.sido} {s.sigungu} {s.dong}'} for s in located[:500]]
    counts=list(qs.values('brand__name').annotate(total=Count('id')).order_by('-total')[:20])
    return JsonResponse({'points':points,'total':len(located) if circle else qs.count(),'located':len(located) if circle else located.count(),'limit':500,'counts':[] if circle else counts,'source':'verified_owner_public_locations'},json_dumps_params={'ensure_ascii':False})

@login_required
@require_GET
def area_options(request):
    qs=public_stores()
    if request.GET.get('region'):qs=qs.filter(sido=request.GET['region'])
    districts=list(qs.exclude(sigungu='').order_by('sigungu').values_list('sigungu',flat=True).distinct())
    if request.GET.get('sigungu'):qs=qs.filter(sigungu=request.GET['sigungu'])
    dongs=list(qs.exclude(dong='').order_by('dong').values_list('dong',flat=True).distinct())
    return JsonResponse({'districts':districts,'dongs':dongs,'source':'registered_stores','manual_entry_allowed':True},json_dumps_params={'ensure_ascii':False})
