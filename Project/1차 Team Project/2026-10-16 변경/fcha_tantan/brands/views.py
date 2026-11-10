import csv
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from .models import Brand
from .constants import REGIONS


def visible_brands():
    # 실제 브랜드가 들어오면 예시 브랜드를 목록에서 제외합니다.
    qs = Brand.objects.all()
    if qs.filter(is_demo=False).exists():
        qs = qs.filter(is_demo=False)
    return qs.prefetch_related('annual_stats__regional_stats').order_by('id')


def context_for(request):
    # 여러 화면에서 함께 사용하는 연도, 비교함, 관심 목록입니다.
    brands = list(visible_brands())
    stats = []
    years = []
    available = []
    sources = []
    updated_at = ''
    is_demo = bool(brands)
    for brand in brands:
        available.append(brand.slug)
        if not brand.is_demo:
            is_demo = False
        for stat in brand.annual_stats.all():
            stats.append(stat)
            if stat.year not in years:
                years.append(stat.year)
            if stat.source_label not in sources:
                sources.append(stat.source_label)
            if updated_at == '' or stat.updated_at > updated_at:
                updated_at = stat.updated_at
    years.sort(reverse=True)
    default_year = 2025
    if years:
        default_year = years[0]
    try:
        year = int(request.GET.get('year', default_year))
    except ValueError:
        year = default_year
    if years and year not in years:
        year = default_year

    compare = []
    for slug in request.session.get('tantan-compare', []):
        if slug in available and slug not in compare and len(compare) < 3:
            compare.append(slug)
    saved = []
    for slug in request.session.get('tantan-saved', []):
        if slug in available and slug not in saved:
            saved.append(slug)
    compare_brands = []
    for slug in compare:
        for brand in brands:
            if brand.slug == slug:
                compare_brands.append(brand)
    request.session['tantan-compare'] = compare
    request.session['tantan-saved'] = saved
    sources.sort()
    source_label = ' / '.join(sources)
    if not source_label:
        source_label = '데이터 없음'
    context = {
        'all_brands': brands,
        'years': years,
        'year': year,
        'regions': REGIONS,
        'is_demo': is_demo,
        'source_label': source_label,
        'updated_at': updated_at,
        'compare_ids': compare,
        'saved_ids': saved,
        'compare_brands': compare_brands,
        'categories': ['전체', '카페', '치킨', '편의점', '미용실'],
        'sorts': [('stores', '매장 수 많은 순'), ('sales', '평균 월 매출 높은 순'),
                  ('opened', '신규 개업 많은 순'), ('closed', '폐업 수 적은 순'), ('name', '브랜드 이름순')],
    }
    return context


def brand_row(brand, year, region='전국'):
    # 선택 연도에 해당하는 통계를 찾습니다. 없으면 None입니다.
    stat = None
    for annual in brand.annual_stats.all():
        if annual.year == year:
            stat = annual
            break
    region_counts = {}
    monthly = None
    if stat:
        for regional in stat.regional_stats.all():
            region_counts[regional.region] = regional.stores
        if stat.annual_sales_krw is not None:
            monthly = round(stat.annual_sales_krw / 12 / 10000)
    if stat and region == '전국':
        stores = stat.stores
    else:
        stores = region_counts.get(region)
    return {'brand': brand, 'stat': stat, 'monthly': monthly, 'stores': stores, 'region_counts': region_counts}


def list_context(request, saved_only=False):
    context = context_for(request)
    query = request.GET.get('query', '').strip()
    category = request.GET.get('category', '전체')
    region = request.GET.get('region', '전국')
    sort = request.GET.get('sort', 'stores')
    if category not in context['categories']:
        category = '전체'
    if region not in ['전국', *REGIONS]:
        region = '전국'
    if sort not in dict(context['sorts']):
        sort = 'stores'
    rows = []
    for brand in context['all_brands']:
        if saved_only and brand.slug not in context['saved_ids']:
            continue
        if query and query not in brand.name and query not in brand.category:
            continue
        if category != '전체' and brand.category != category:
            continue
        row = brand_row(brand, context['year'], region)
        if region != '전국' and not row['stores']:
            continue
        rows.append(row)
    if sort == 'name':
        rows.sort(key=lambda row: row['brand'].name)
    elif sort == 'closed':
        rows.sort(key=lambda row: row['stat'].closed if row['stat'] and row['stat'].closed is not None else float('inf'))
    else:
        def value(row):
            v = None
            if sort == 'sales':
                v = row['monthly']
            elif sort == 'opened' and row['stat']:
                v = row['stat'].opened
            elif sort == 'stores':
                v = row['stores']
            if v is None:
                return -1
            return v
        rows.sort(key=value, reverse=True)
    context.update(rows=rows, query=query, category=category, region=region, sort=sort,
                   saved_only=saved_only, page='saved' if saved_only else 'list')
    return context


@require_GET
def blist(request):
    return render(request, 'blist.html', list_context(request))


@require_GET
def bsaved(request):
    return render(request, 'bsaved.html', list_context(request, saved_only=True))


@require_GET
def bview(request, slug):
    context = context_for(request)
    brand = get_object_or_404(visible_brands(), slug=slug)
    row = brand_row(brand, context['year'])
    regions = [{'name': name, 'count': row['region_counts'].get(name)} for name in REGIONS]
    maximum = max([r['count'] or 0 for r in regions] + [1])
    for region in regions:
        region['width'] = round((region['count'] or 0) / maximum * 100, 2)
    top_regions = sorted(regions, key=lambda r: r['count'] if r['count'] is not None else -1, reverse=True)[:7]
    trend = list(brand.annual_stats.all())
    maximum = max([v or 0 for s in trend for v in [s.opened, s.closed]] + [1])
    chart = [{'year': s.year, 'opened': s.opened, 'closed': s.closed,
              'opened_height': round((s.opened or 0) / maximum * 85, 2),
              'closed_height': round((s.closed or 0) / maximum * 85, 2)} for s in trend]
    context.update(page='detail', row=row, brand=brand, regional_rows=regions,
                   top_regions=top_regions, chart=chart, costs=brand.costs.items())
    return render(request, 'bview.html', context)


def selected_rows(context):
    rows = []
    for brand in context['compare_brands']:
        rows.append(brand_row(brand, context['year']))
    return rows


@require_GET
def bcompare(request):
    context = context_for(request)
    rows = selected_rows(context)
    comparisons = [
        ('연말 매장 수', [r['stores'] for r in rows], '개'),
        ('연간 신규 개업', [r['stat'].opened if r['stat'] else None for r in rows], '개'),
        ('연간 폐업', [r['stat'].closed if r['stat'] else None for r in rows], '개'),
        ('평균 월 매출', [r['monthly'] for r in rows], '만원'),
        ('창업비용 (만원)', [round(r['brand'].initial_cost_krw / 10000) if r['brand'].initial_cost_krw is not None else None for r in rows], '만원'),
        ('기준 면적', [r['brand'].area_sqm for r in rows], '㎡'),
    ]
    comparisons += [(f'{name} 매장 수', [r['region_counts'].get(name) for r in rows], '개') for name in REGIONS]
    context.update(page='compare', rows=rows, comparisons=comparisons)
    return render(request, 'bcompare.html', context)


@require_GET
def bregion(request):
    context = context_for(request)
    region = request.GET.get('region', '서울')
    if region not in REGIONS:
        region = '서울'
    rows = [brand_row(b, context['year'], region) for b in context['all_brands']]
    rows.sort(key=lambda r: r['stores'] if r['stores'] is not None else -1, reverse=True)
    for row in rows:
        row['share'] = round(row['stores'] / row['stat'].stores * 100, 1) if row['stores'] is not None and row['stat'] and row['stat'].stores else None
    tiles = [{'name': name, 'total': sum(r['region_counts'].get(name) or 0 for r in rows)} for name in REGIONS]
    context.update(page='regions', region=region, rows=rows, tiles=tiles,
                   total=sum(r['stores'] or 0 for r in rows), active_count=sum(bool(r['stores']) for r in rows))
    return render(request, 'bregion.html', context)


@require_GET
def guide(request):
    context = context_for(request)
    context['page'] = 'guide'
    return render(request, 'guide.html', context)


def return_to_page(request):
    target = request.POST.get('next', reverse('brands:blist'))
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse('brands:blist')
    return redirect(target)


@require_POST
def compare_toggle(request, slug):
    brand = get_object_or_404(visible_brands(), slug=slug)
    context = context_for(request)
    selected = context['compare_ids']
    if brand.slug in selected:
        selected.remove(brand.slug)
    elif len(selected) >= 3:
        messages.info(request, '최대 3개 브랜드까지 비교할 수 있어요. 기존 브랜드를 먼저 빼주세요.')
    else:
        selected.append(brand.slug)
    request.session['tantan-compare'] = selected
    return return_to_page(request)


@require_POST
def compare_clear(request):
    request.session['tantan-compare'] = []
    return return_to_page(request)


@require_POST
def saved_toggle(request, slug):
    brand = get_object_or_404(visible_brands(), slug=slug)
    selected = context_for(request)['saved_ids']
    if brand.slug in selected:
        selected.remove(brand.slug)
    else:
        selected.append(brand.slug)
    request.session['tantan-saved'] = selected
    return return_to_page(request)


@require_GET
def compare_csv(request):
    context = context_for(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="tantan_compare_{context["year"]}.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['데이터 구분', '기준연도', '브랜드', '전국 매장 수', '연간 개업 수', '연간 폐업 수', '평균 월 매출(만원)', '창업비용(원)'])
    def safe(value):
        text = str(value) if value is not None else ''
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
    for row in selected_rows(context):
        s = row['stat']
        values = ['가상 예시' if row['brand'].is_demo else '실제 데이터', context['year'], row['brand'].name,
                  row['stores'], s.opened if s else None, s.closed if s else None, row['monthly'], row['brand'].initial_cost_krw]
        writer.writerow([safe(v) for v in values])
    return response
